from datetime import timedelta
from io import BytesIO

import freezegun
import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.core import error_codes
from apps.core.services.images import (
    ImageDimensionsTooLargeError,
    ImageTooLargeError,
    ImageUnsupportedFormatError,
    InvalidImageError,
)
from apps.events.factories import CategoryFactory, EventFactory
from apps.events.models import Event, EventStatus


def make_uploaded_image(image_format='PNG', size=(200, 100)):
    image = Image.new('RGB', size, color='red')
    buffer = BytesIO()
    image.save(buffer, format=image_format)

    extension = {'BMP': 'bmp', 'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}[image_format]
    return SimpleUploadedFile(
        f'image.{extension}',
        buffer.getvalue(),
        content_type=f'image/{extension}',
    )


class TestListCreateEventView:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.category = CategoryFactory.create()
        self.payload = {
            'title': 'New event',
            'description': 'Description for the new event',
            'category': self.category.pk,
            'address': '123 Example Street',
            'start_at': timezone.now() + timedelta(days=7),
            'end_at': timezone.now() + timedelta(days=8),
            'capacity': 100,
            'price': '25.00',
            'status': EventStatus.DRAFT,
        }
        self.url = reverse('list-create-event')

    def test_get_success_and_is_paginated(self, api_client):
        matching_event = EventFactory.create(
            status=EventStatus.PUBLISHED,
            category=self.category,
            title='Matching filter smoke test',
        )
        EventFactory.create(
            status=EventStatus.PUBLISHED,
            title='Matching filter smoke test',
        )

        response = api_client.get(
            self.url,
            data={'search': 'Matching filter smoke test', 'category': self.category.pk},
        )

        assert response.status_code == 200
        assert {'count', 'next', 'previous', 'results'} == set(response.json().keys())
        assert response.json()['count'] == 1
        assert response.json()['results'][0]['id'] == matching_event.pk

    def test_get_returns_only_events_not_in_draft_status(self, api_client):
        published_event = EventFactory.create(status=EventStatus.PUBLISHED)
        completed_event = EventFactory.create(status=EventStatus.COMPLETED)
        cancelled_event = EventFactory.create(status=EventStatus.CANCELLED)
        EventFactory.create(status=EventStatus.DRAFT)

        response = api_client.get(self.url)

        assert response.status_code == 200
        result_ids = {event['id'] for event in response.json()['results']}
        assert result_ids == {
            published_event.pk,
            completed_event.pk,
            cancelled_event.pk,
        }

    @pytest.mark.parametrize('search_field', ('title', 'description', 'address'))
    def test_search_filter_is_case_insensitive(self, api_client, search_field):
        event_values = {
            'title': 'Different title',
            'description': 'Different description',
            'address': 'Different address',
        }
        event_values[search_field] = 'MixedCaseSearchTerm'
        event = EventFactory.create(status=EventStatus.PUBLISHED, **event_values)
        EventFactory.create(
            status=EventStatus.PUBLISHED,
            title='Another title',
            description='Another description',
            address='Another address',
        )

        response = api_client.get(self.url, data={'search': 'mixedcasesearchterm'})

        assert response.status_code == 200
        results = response.json()['results']
        assert len(results) == 1
        assert results[0]['id'] == event.pk

    def test_post_requires_verified_user(self, auth_client):
        response = auth_client.post(self.url, data=self.payload, format='json')

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'

    def test_post_success(self, user, verified_client):
        response = verified_client.post(self.url, data=self.payload, format='json')

        assert response.status_code == 201
        assert Event.objects.count() == 1
        event = Event.objects.get()
        assert event.user == user
        assert event.category == self.category
        assert event.title == self.payload['title']
        assert event.status == EventStatus.DRAFT
        assert response.json()['id'] == event.pk


class TestRetrieveUpdateEventView:
    def test_get_success(self, user, auth_client):
        event = EventFactory.create(user=user)

        response = auth_client.get(reverse('retrieve-update-event', kwargs={'id': event.pk}))

        assert response.status_code == 200
        assert response.json()['id'] == event.pk
        assert response.json()['title'] == event.title

    @pytest.mark.parametrize('status', (EventStatus.PUBLISHED, EventStatus.COMPLETED, EventStatus.CANCELLED))
    def test_get_non_draft_event_is_visible_to_regular_user(self, other_user, api_client, status):
        event = EventFactory.create(user=other_user, status=status)

        response = api_client.get(reverse('retrieve-update-event', kwargs={'id': event.pk}))

        assert response.status_code == 200
        assert response.json()['id'] == event.pk

    @pytest.mark.parametrize('status', EventStatus.values)
    def test_get_any_status_event_is_visible_to_owner(self, user, status, auth_client):
        event = EventFactory.create(user=user, status=status)

        response = auth_client.get(reverse('retrieve-update-event', kwargs={'id': event.pk}))

        assert response.status_code == 200
        assert response.json()['id'] == event.pk

    @pytest.mark.parametrize('status', EventStatus.values)
    def test_get_any_status_event_is_visible_to_admin(self, user, other_user, status, auth_client):
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        event = EventFactory.create(user=other_user, status=status)

        response = auth_client.get(reverse('retrieve-update-event', kwargs={'id': event.pk}))

        assert response.status_code == 200
        assert response.json()['id'] == event.pk

    def test_get_non_owned_draft_event_returns_404(self, other_user, api_client):
        event = EventFactory.create(user=other_user, status=EventStatus.DRAFT)

        response = api_client.get(reverse('retrieve-update-event', kwargs={'id': event.pk}))

        assert response.status_code == 404
        assert response.json()['error']['code'] == 'not_found'

    def test_get_nonexistent_event_returns_404(self, db, api_client):
        response = api_client.get(reverse('retrieve-update-event', kwargs={'id': 0}))

        assert response.status_code == 404
        assert response.json()['error']['code'] == 'not_found'

    def test_patch_success(self, user, verified_client):
        event = EventFactory.create(user=user, title='Original title')
        payload = {'title': 'Updated title'}

        response = verified_client.patch(reverse('retrieve-update-event', kwargs={'id': event.pk}), data=payload, format='json')

        assert response.status_code == 200
        assert response.json()['title'] == payload['title']
        event.refresh_from_db()
        assert event.title == payload['title']

    def test_patch_success_for_admin(self, user, other_user, verified_client):
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        event = EventFactory.create(user=other_user, title='Original title')
        payload = {'title': 'Updated by admin'}

        response = verified_client.patch(reverse('retrieve-update-event', kwargs={'id': event.pk}), data=payload, format='json')

        assert response.status_code == 200
        assert response.json()['title'] == payload['title']
        event.refresh_from_db()
        assert event.title == payload['title']

    def test_patch_requires_verified_user(self, user, auth_client):
        event = EventFactory.create(user=user, title='Original title')

        response = auth_client.patch(
            reverse('retrieve-update-event', kwargs={'id': event.pk}),
            data={'title': 'Updated title'},
            format='json',
        )

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'
        event.refresh_from_db()
        assert event.title == 'Original title'

    def test_patch_requires_owner(self, other_user, verified_client):
        event = EventFactory.create(user=other_user, status=EventStatus.PUBLISHED)

        response = verified_client.patch(
            reverse('retrieve-update-event', kwargs={'id': event.pk}),
            data={'title': 'Updated title'},
            format='json',
        )

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'
        event.refresh_from_db()
        assert event.title != 'Updated title'

    @pytest.mark.parametrize('status', (EventStatus.COMPLETED, EventStatus.CANCELLED))
    def test_patch_completed_or_cancelled_event_returns_error_code(self, user, verified_client, status):
        event = EventFactory.create(user=user, status=status)
        original_title = event.title

        response = verified_client.patch(
            reverse('retrieve-update-event', kwargs={'id': event.pk}),
            data={'title': 'Updated title'},
            format='json',
        )

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.COMPLETED_OR_CANCELLED_EVENT_NOT_EDITABLE
        event.refresh_from_db()
        assert event.title == original_title

    def test_patch_published_event_organizer_returns_error_code(self, user, other_user, verified_client):
        event = EventFactory.create(user=user, status=EventStatus.PUBLISHED)

        response = verified_client.patch(
            reverse('retrieve-update-event', kwargs={'id': event.pk}),
            data={'user': other_user.pk},
            format='json',
        )

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.USER_IN_PUBLISHED_EVENT_NOT_EDITABLE
        event.refresh_from_db()
        assert event.user_id == user.pk


class TestUploadEventImageView:
    def get_url(self, event_id):
        return reverse('upload-event-image', kwargs={'id': event_id})

    def test_put_success_image_is_available_by_returned_url(self, user, verified_client):
        event = EventFactory.create(user=user)

        response = verified_client.put(
            self.get_url(event.pk),
            data={'image': make_uploaded_image()},
            format='multipart',
        )

        assert response.status_code == 200
        image_url = response.json()['image']
        event.refresh_from_db()
        assert image_url == event.image.url
        assert image_url

        with (
            default_storage.open(event.image.name) as stored_image,
            Image.open(stored_image) as image,
        ):
            assert image.format == 'WEBP'

    def test_put_success_for_admin(self, user, other_user, verified_client):
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        event = EventFactory.create(user=other_user)

        response = verified_client.put(
            self.get_url(event.pk),
            data={'image': make_uploaded_image()},
            format='multipart',
        )

        assert response.status_code == 200

    def test_put_requires_owner_or_admin(self, other_user, verified_client):
        event = EventFactory.create(user=other_user)

        response = verified_client.put(
            self.get_url(event.pk),
            data={'image': make_uploaded_image()},
            format='multipart',
        )

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'

    def test_put_requires_verified_user(self, user, auth_client):
        event = EventFactory.create(user=user)

        response = auth_client.put(
            self.get_url(event.pk),
            data={'image': make_uploaded_image()},
            format='multipart',
        )

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'

    @pytest.mark.parametrize(('error', 'code'),
        [
            (InvalidImageError, error_codes.INVALID_IMAGE),
            (ImageUnsupportedFormatError, error_codes.UNSUPPORTED_IMAGE_FORMAT),
            (ImageTooLargeError, error_codes.IMAGE_TOO_LARGE),
            (ImageDimensionsTooLargeError, error_codes.IMAGE_DIMENSIONS_TOO_LARGE),
        ],
    )
    def test_put_process_image_error_returns_error_code(self, user, verified_client, mocker, error, code):
        event = EventFactory.create(user=user)
        mocker.patch('apps.events.services.events.process_image', side_effect=error)

        response = verified_client.put(
            self.get_url(event.pk),
            data={'image': make_uploaded_image()},
            format='multipart',
        )

        assert response.status_code == 400
        assert response.json()['error']['code'] == code

    @pytest.mark.parametrize('status', (EventStatus.COMPLETED, EventStatus.CANCELLED))
    def test_put_completed_or_cancelled_event_returns_error_code(self, user, verified_client, status):
        event = EventFactory.create(user=user, status=status)

        response = verified_client.put(
            self.get_url(event.pk),
            data={'image': make_uploaded_image()},
            format='multipart',
        )

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.COMPLETED_OR_CANCELLED_EVENT_NOT_EDITABLE

    def test_put_nonexistent_event_returns_not_found_error_code(self, db, verified_client):
        response = verified_client.put(
            self.get_url(0),
            data={'image': make_uploaded_image()},
            format='multipart',
        )

        assert response.status_code == 404
        assert response.json()['error']['code'] == 'not_found'


class TestEventPublishView:
    def get_url(self, event_id):
        return reverse('publish-event', kwargs={'id': event_id})

    def test_post_success_for_owner(self, user, verified_client):
        event = EventFactory.create(user=user)
        event.image.save('event.png', ContentFile(b'image'), save=True)

        response = verified_client.post(self.get_url(event.pk))

        assert response.status_code == 200
        event.refresh_from_db()
        assert event.status == EventStatus.PUBLISHED

    def test_post_success_for_admin(self, user, other_user, verified_client):
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        event = EventFactory.create(user=other_user)
        event.image.save('event.png', ContentFile(b'image'), save=True)

        response = verified_client.post(self.get_url(event.pk))

        assert response.status_code == 200

    def test_post_requires_owner_or_admin(self, other_user, verified_client):
        event = EventFactory.create(user=other_user)
        event.image.save('event.png', ContentFile(b'image'), save=True)

        response = verified_client.post(self.get_url(event.pk))

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'

    def test_post_nonexistent_event_returns_not_found_error_code(self, db, verified_client):
        response = verified_client.post(self.get_url(0))

        assert response.status_code == 404
        assert response.json()['error']['code'] == 'not_found'

    @pytest.mark.parametrize('status', (EventStatus.PUBLISHED, EventStatus.COMPLETED, EventStatus.CANCELLED))
    def test_post_event_not_in_draft_status_returns_invalid_event_transition(self, user, verified_client, status):
        event = EventFactory.create(user=user, status=status)
        event.image.save('event.png', ContentFile(b'image'), save=True)

        response = verified_client.post(self.get_url(event.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.INVALID_EVENT_TRANSITION

    def test_post_started_event_returns_not_publishable(self, user, verified_client):
        event = EventFactory.create(
            user=user,
            start_at=timezone.now() - timedelta(seconds=1),
        )
        event.image.save('event.png', ContentFile(b'image'), save=True)

        response = verified_client.post(self.get_url(event.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.EVENT_NOT_PUBLISHABLE

    def test_post_event_without_image_returns_not_publishable(self, user, verified_client):
        event = EventFactory.create(user=user)

        response = verified_client.post(self.get_url(event.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.EVENT_NOT_PUBLISHABLE


class TestEventCancelView:
    def get_url(self, event_id):
        return reverse('cancel-event', kwargs={'id': event_id})

    def test_post_success_for_owner_and_updates_status_and_updated_at(self, user, verified_client):
        with freezegun.freeze_time('2025-01-01 10:00:00'):
            event = EventFactory.create(user=user, status=EventStatus.PUBLISHED)
            original_updated_at = event.updated_at

        with freezegun.freeze_time('2025-01-01 10:15:00'):
            response = verified_client.post(self.get_url(event.pk))
            event.refresh_from_db()
            updated_at = timezone.now()

        assert response.status_code == 200
        assert event.status == EventStatus.CANCELLED
        assert event.updated_at == updated_at
        assert event.updated_at != original_updated_at

    def test_post_success_for_admin(self, user, other_user, verified_client):
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        event = EventFactory.create(user=other_user, status=EventStatus.PUBLISHED)

        response = verified_client.post(self.get_url(event.pk))

        assert response.status_code == 200

    def test_post_requires_owner_or_admin(self, other_user, verified_client):
        event = EventFactory.create(user=other_user, status=EventStatus.PUBLISHED)

        response = verified_client.post(self.get_url(event.pk))

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'

    def test_post_nonexistent_event_returns_not_found_error_code(self, db, verified_client):
        response = verified_client.post(self.get_url(0))

        assert response.status_code == 404
        assert response.json()['error']['code'] == 'not_found'

    @pytest.mark.parametrize('status', (EventStatus.COMPLETED, EventStatus.CANCELLED))
    def test_post_completed_or_cancelled_event_returns_invalid_event_transition(self, user, verified_client, status):
        event = EventFactory.create(user=user, status=status)

        response = verified_client.post(self.get_url(event.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.INVALID_EVENT_TRANSITION

    def test_post_draft_event_returns_invalid_event_transition(self, user, verified_client):
        event = EventFactory.create(user=user, status=EventStatus.DRAFT)

        response = verified_client.post(self.get_url(event.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.INVALID_EVENT_TRANSITION
