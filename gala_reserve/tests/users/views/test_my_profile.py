from io import BytesIO

import pytest
from apps.booking.factories import RegistrationFactory, TicketFactory
from apps.core import error_codes
from apps.core.services.images import (
    ImageDimensionsTooLargeError,
    ImageTooLargeError,
    ImageUnsupportedFormatError,
    InvalidImageError,
)
from apps.events.factories import EventFactory
from apps.events.models import EventStatus
from apps.users.factories import UserFactory
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image


def make_uploaded_photo(image_format='PNG', size=(200, 100)):
    image = Image.new('RGB', size, color='red')
    buffer = BytesIO()
    image.save(buffer, format=image_format)

    extension = {'BMP': 'bmp', 'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}[image_format]
    return SimpleUploadedFile(
        f'image.{extension}',
        buffer.getvalue(),
        content_type=f'image/{extension}',
    )


class TestMyProfileView:
    def test_get_success(self, user, auth_client):
        response = auth_client.get(reverse('my-profile'))
        response_body = response.json()

        assert response.status_code == 200
        assert 'id' in response_body
        assert response_body['id'] == user.pk
        assert 'password' not in response_body

    def test_patch_success(self, user, auth_client):
        payload = {
            'username': 'test_username',
            'first_name': 'TestFirstName',
            'last_name': 'TestLastName',
            'bio': 'test bio'
        }

        response = auth_client.patch(reverse('my-profile'), payload, format='json')

        assert response.status_code == 200

        user.refresh_from_db()

        for field, value in payload.items():
            assert getattr(user, field) == value

    def test_patch_unique_username_returns_400(self, user, auth_client):
        other_user = UserFactory.create(username='TestUser')

        payload = {'username': other_user.username}
        response = auth_client.patch(reverse('my-profile'), payload, format='json')

        assert response.status_code == 400
        assert response.json()['error']['code'] == 'invalid'
        user.refresh_from_db()
        assert user.username != other_user.username

    def test_requires_authentication(self, api_client):
        response = api_client.get(reverse('my-profile'))

        assert response.status_code == 401
        assert response.json()['error']['code'] == 'not_authenticated'


class TestMyEventsView:
    def test_get_success_and_is_paginated_with_only_users_events(self, user, other_user, verified_client):
        user_events = [
            EventFactory.create(user=user, status=status)
            for status in EventStatus.values
        ]
        EventFactory.create(user=other_user)
        url = reverse('my-events')

        response = verified_client.get(url)
        response_body = response.json()

        assert response.status_code == 200
        assert {'count', 'next', 'previous', 'results'} == set(response_body.keys())
        assert {event['id'] for event in response_body['results']} == {event.pk for event in user_events}

    def test_get_requires_verified_user(self, auth_client):
        response = auth_client.get(reverse('my-events'))

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'email_not_verified'


class TestMyRegistrationsView:
    def test_get_success_and_is_paginated_with_only_users_registrations(self, user, other_user, auth_client):
        user_registrations = [
            RegistrationFactory.create(user=user),
            RegistrationFactory.create(user=user),
        ]
        RegistrationFactory.create(user=other_user)

        response = auth_client.get(reverse('my-registrations'))
        response_body = response.json()

        assert response.status_code == 200
        assert {'count', 'next', 'previous', 'results'} == set(response_body.keys())
        assert response_body['count'] == len(user_registrations)
        assert {registration['id'] for registration in response_body['results']} == {
            registration.pk for registration in user_registrations
        }

    def test_get_requires_authentication(self, api_client):
        response = api_client.get(reverse('my-registrations'))

        assert response.status_code == 401
        assert response.json()['error']['code'] == 'not_authenticated'


class TestMyTicketsView:
    def test_get_success_and_is_paginated_with_only_users_tickets(self, user, other_user, auth_client):
        user_tickets = [
            TicketFactory.create(registration=RegistrationFactory.create(user=user)),
            TicketFactory.create(registration=RegistrationFactory.create(user=user)),
        ]
        TicketFactory.create(registration=RegistrationFactory.create(user=other_user))

        response = auth_client.get(reverse('my-tickets'))
        response_body = response.json()

        assert response.status_code == 200
        assert {'count', 'next', 'previous', 'results'} == set(response_body.keys())
        assert response_body['count'] == len(user_tickets)
        assert {ticket['id'] for ticket in response_body['results']} == {
            str(ticket.pk) for ticket in user_tickets
        }

    def test_get_requires_authentication(self, api_client):
        response = api_client.get(reverse('my-tickets'))

        assert response.status_code == 401
        assert response.json()['error']['code'] == 'not_authenticated'


class TestMyProfileUploadPhotoView:
    def get_url(self):
        return reverse('set-profile-photo')

    def test_put_success_photo_is_available_by_returned_url(self, user, auth_client):
        response = auth_client.put(
            self.get_url(),
            data={'photo': make_uploaded_photo()},
            format='multipart',
        )

        assert response.status_code == 200
        photo_url = response.json()['photo']
        user.refresh_from_db()
        assert photo_url == user.photo.url
        assert photo_url

        with (
            default_storage.open(user.photo.name) as stored_photo,
            Image.open(stored_photo) as image,
        ):
            assert image.format == 'WEBP'

    @pytest.mark.parametrize(('error', 'code'),
        [
            (InvalidImageError, error_codes.INVALID_IMAGE),
            (ImageUnsupportedFormatError, error_codes.UNSUPPORTED_IMAGE_FORMAT),
            (ImageTooLargeError, error_codes.IMAGE_TOO_LARGE),
            (ImageDimensionsTooLargeError, error_codes.IMAGE_DIMENSIONS_TOO_LARGE),
        ],
    )
    def test_put_process_photo_error_returns_error_code(self, auth_client, mocker, error, code):
        mocker.patch('apps.users.services.profile.process_image', side_effect=error)

        response = auth_client.put(
            self.get_url(),
            data={'photo': make_uploaded_photo()},
            format='multipart',
        )

        assert response.status_code == 400
        assert response.json()['error']['code'] == code

    def test_put_requires_authentication(self, api_client):
        response = api_client.put(
            self.get_url(),
            data={'photo': make_uploaded_photo()},
            format='multipart',
        )

        assert response.status_code == 401
        assert response.json()['error']['code'] == 'not_authenticated'