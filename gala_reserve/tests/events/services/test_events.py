from decimal import Decimal
from io import BytesIO

import freezegun
import pytest
from apps.events.factories import EventFactory
from apps.events.models import Event, EventStatus
from apps.events.services.events import (
    CompleteOrCancelledEventNotEditable,
    UserInPublishedEventNotEditableError,
    event_set_image,
    event_update,
)
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework import exceptions


def make_image(image_format='PNG', size=(2000, 1000)):
    image = Image.new('RGB', size, color='red')
    buffer = BytesIO()
    image.save(buffer, format=image_format)

    extension = {'BMP': 'bmp', 'JPEG': 'jpg', 'PNG': 'png'}[image_format]
    return SimpleUploadedFile(
        f'image.{extension}',
        buffer.getvalue(),
        content_type=f'image/{extension}',
    )


class TestEventUpdate:
    def test_normal_update_changes_only_input_fields(self, user):
        with freezegun.freeze_time('2014-02-15 12:00:00'):
            event = EventFactory.create(user=user, capacity=100, price=Decimal('10.00'))
            last_update = timezone.now()

        assert event.updated_at == last_update

        new_values = {
            'title': 'Updated event',
            'description': 'Updated description',
            'address': 'New address',
            'capacity': 200,
            'price': Decimal('25.00'),
        }
        unchanged_values = {
            'image': event.image.name or '',
            **{
                field: getattr(event, field)
                for field in (
                    'category_id',
                    'user_id',
                    'start_at',
                    'end_at',
                    'seats_taken',
                    'status',
                    'created_at',
                    'published_at',
                )
            },
        }

        with freezegun.freeze_time('2014-02-15 12:15:00'):
            updated_event = event_update(event_id=event.pk, event_input=new_values)
            last_update = timezone.now()

            event.refresh_from_db()
            assert event.updated_at == last_update

        assert updated_event.pk == event.pk
        for field, value in new_values.items():
            assert getattr(event, field) == value
            assert getattr(updated_event, field) == value

        for field, value in unchanged_values.items():
            current_value = getattr(event, field)
            if field == 'image':
                current_value = current_value.name
            assert current_value == value

    def test_published_event_update_without_user_id(self, user):
        event = EventFactory.create(user=user, status=EventStatus.PUBLISHED)

        updated_event = event_update(
            event_id=event.pk,
            event_input={'title': 'Updated published event'},
        )

        event.refresh_from_db()
        assert updated_event.title == 'Updated published event'
        assert event.title == 'Updated published event'
        assert event.user_id == user.pk
        assert event.status == EventStatus.PUBLISHED

    def test_event_does_not_exist(self, db):
        with pytest.raises(exceptions.NotFound):
            event_update(event_id=0, event_input={'title': 'Updated event'})

    @pytest.mark.parametrize('status', (EventStatus.COMPLETED, EventStatus.CANCELLED))
    def test_completed_or_cancelled_event_is_not_editable(self, user, status):
        event = EventFactory.create(user=user, status=status)

        with pytest.raises(CompleteOrCancelledEventNotEditable):
            event_update(
                event_id=event.pk,
                event_input={'title': 'Updated event'},
            )

        event.refresh_from_db()
        assert event.title != 'Updated event'

    def test_published_event_organizer_is_not_editable(self, user, other_user):
        event = EventFactory.create(user=user, status=EventStatus.PUBLISHED)

        with pytest.raises(UserInPublishedEventNotEditableError):
            event_update(
                event_id=event.pk,
                event_input={'user_id': other_user.pk},
            )

        event.refresh_from_db()
        assert event.user_id == user.pk


class TestEventSetImage:
    def test_replaces_event_image_with_resized_webp(self, user):
        event = EventFactory.create(user=user)
        event.image.save('old.png', ContentFile(b'old image'), save=True)
        old_image_name = event.image.name

        updated_event = event_set_image(
            event_id=event.pk,
            image=make_image(size=(3000, 1500)),
        )
        event.refresh_from_db()

        assert updated_event.pk == event.pk
        assert event.image.name != old_image_name
        assert event.image.name.endswith('.webp')
        with Image.open(event.image) as image:
            assert image.format == 'WEBP'
            assert image.size[0] <= Event.THUMBNAIL_SIZE_PX[0]
            assert image.size[1] <= Event.THUMBNAIL_SIZE_PX[1]

    def test_event_does_not_exist(self, db):
        with pytest.raises(exceptions.NotFound):
            event_set_image(event_id=0, image=make_image())

    @pytest.mark.parametrize('status', (EventStatus.COMPLETED, EventStatus.CANCELLED))
    def test_completed_or_cancelled_event_is_not_editable(self, user, status):
        event = EventFactory.create(user=user, status=status)

        with pytest.raises(CompleteOrCancelledEventNotEditable):
            event_set_image(event_id=event.pk, image=make_image())

        event.refresh_from_db()
        assert not event.image