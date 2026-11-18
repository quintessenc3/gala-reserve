from django.core.files import File
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import exceptions, status

from apps.booking.models import (
    RegistrationCancelReason,
    RegistrationStatus,
    TicketStatus,
)
from apps.core import error_codes
from apps.core.exceptions import DomainError
from apps.core.services.images import process_image
from apps.events.models import Event, EventStatus


class CompleteOrCancelledEventNotEditable(DomainError):
    code = error_codes.COMPLETED_OR_CANCELLED_EVENT_NOT_EDITABLE
    message = 'Нельзя редактировать завершенное или отмененное мероприятие.'
    http_status = status.HTTP_409_CONFLICT


class UserInPublishedEventNotEditableError(DomainError):
    code = error_codes.USER_IN_PUBLISHED_EVENT_NOT_EDITABLE
    message = 'Нельзя редактировать организатора мероприятия, если оно уже опубликовано.'
    http_status = status.HTTP_409_CONFLICT


class EventNotPublishableError(DomainError):
    code = error_codes.EVENT_NOT_PUBLISHABLE
    message = 'Нельзя опубликовать это мероприятие.'
    http_status = status.HTTP_409_CONFLICT


class PublishAlreadyPublishedEventError(DomainError):
    code = error_codes.INVALID_EVENT_TRANSITION
    message = 'Нельзя опубликовать мероприятие, которое уже было опубликовано.'
    http_status = status.HTTP_409_CONFLICT


class CancelAlreadyCompletedEventError(DomainError):
    code = error_codes.INVALID_EVENT_TRANSITION
    message = 'Нельзя отменить мероприятие, которое уже было отменено или завершено.'
    http_status = status.HTTP_409_CONFLICT


class CancelDraftEventError(DomainError):
    code = error_codes.INVALID_EVENT_TRANSITION
    message = 'Нельзя отменить мероприятие в состоянии черновика.'
    http_status = status.HTTP_409_CONFLICT


class CancelAlreadyStartedEventError(DomainError):
    code = error_codes.EVENT_ALREADY_STARTED
    message = 'Нельзя отменить мероприятие, которое уже началось.'
    http_status = status.HTTP_409_CONFLICT


def event_update(
        *, 
        event_id: int,
        event_input: dict
    ) -> Event:
    '''
    Сервис обновления мероприятия.
    '''

    with transaction.atomic():
        event = Event.objects.select_for_update().filter(pk=event_id).first()
        if event is None:
            raise exceptions.NotFound(detail='Мероприятия не существует.')

        if event.status in (EventStatus.COMPLETED, EventStatus.CANCELLED):
            raise CompleteOrCancelledEventNotEditable
        elif event.status == EventStatus.PUBLISHED and (
            event_input.get('user_id', None) or
            event_input.get('user', None)
        ) is not None:
            raise UserInPublishedEventNotEditableError

        for field, value in event_input.items():
            setattr(event, field, value)

        event.save(update_fields=[*event_input.keys(), 'updated_at'])

    return event


def event_set_image(*, event_id: int, image: File) -> Event:
    '''
    Сервис для установки изображения мероприятия.
    '''

    with transaction.atomic():
        event = Event.objects.select_for_update().filter(pk=event_id).first()
        if event is None:
            raise exceptions.NotFound(detail='Мероприятия не существует.')

        if event.status in (EventStatus.COMPLETED, EventStatus.CANCELLED):
            raise CompleteOrCancelledEventNotEditable

        processed = process_image(
            file=image,
            max_image_size_bytes=Event.MAX_IMAGE_FILE_SIZE_BYTES,
            max_image_resolution_px=Event.MAX_IMAGE_RESOLUTION,
            thumbnail_size_px=Event.THUMBNAIL_SIZE_PX
        )

        event.image.save(processed.name, processed, save=False)
        event.save(update_fields=['image'])

    return event


def event_publish(*, event_id: int) -> Event:
    '''
    Сервис публикации мероприятия.
    '''

    with transaction.atomic():
        event = Event.objects.select_for_update().filter(pk=event_id).first()
        if event is None:
            raise exceptions.NotFound(detail='Мероприятия не существует.')

        if event.status != EventStatus.DRAFT:
            raise PublishAlreadyPublishedEventError

        if not event.image or event.start_at <= timezone.now():
            raise EventNotPublishableError

        event.status = EventStatus.PUBLISHED
        event.published_at = timezone.now()
        event.save(update_fields=['status', 'published_at', 'updated_at'])

    return event


def event_cancel(*, event_id: int) -> Event:
    '''
    Сервис отмены мероприятия.
    '''

    with transaction.atomic():
        event = Event.objects.select_for_update().filter(pk=event_id).first()
        if event is None:
            raise exceptions.NotFound(detail='Мероприятия не существует.')

        if event.status in (EventStatus.COMPLETED, EventStatus.CANCELLED):
            raise CancelAlreadyCompletedEventError
        elif event.status == EventStatus.DRAFT:
            raise CancelDraftEventError

        if timezone.now() >= event.start_at:
            raise CancelAlreadyStartedEventError

        (
            event.registrations
            .filter(
                ~Q(status=RegistrationStatus.CANCELLED),
                cancel_reason='',
                cancelled_at__isnull=True
            )
            .update(
                status=RegistrationStatus.CANCELLED,
                cancel_reason=RegistrationCancelReason.EVENT_CANCELLED,
                cancelled_at=timezone.now()
            )
        )

        (
            event.tickets
            .filter(status=TicketStatus.VALID)
            .update(
                status=TicketStatus.CANCELLED
            )
        )

        event.status = EventStatus.CANCELLED
        event.save(update_fields=['status', 'updated_at'])

    return event