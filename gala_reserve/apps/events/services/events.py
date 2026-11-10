from django.db import transaction
from rest_framework import exceptions, status

from apps.core import error_codes
from apps.core.exceptions import DomainError
from apps.events.models import Event, EventStatus


class CompleteOrCancelledEventNotEditable(DomainError):
    code = error_codes.COMPLETED_OR_CANCELLED_EVENT_NOT_EDITABLE
    message = 'Нельзя редактировать завершенное или отмененное мероприятие.'
    http_status = status.HTTP_409_CONFLICT


class UserInPublishedEventNotEditableError(DomainError):
    code = error_codes.USER_IN_PUBLISHED_EVENT_NOT_EDITABLE
    message = 'Нельзя редактировать организатора мероприятия, если оно уже опубликовано.'
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
        elif event.status == EventStatus.PUBLISHED and event_input.get('user_id', None) is not None:
            raise UserInPublishedEventNotEditableError

        for field, value in event_input.items():
            setattr(event, field, value)

        event.save(update_fields=[*event_input.keys(), 'updated_at'])

    return event