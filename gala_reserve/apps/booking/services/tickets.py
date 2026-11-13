
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import exceptions, status

from apps.booking.models import (
    Ticket,
    TicketStatus,
)
from apps.core import error_codes
from apps.core.exceptions import DomainError


class TicketAlreadyUsedError(DomainError):
    code = error_codes.TICKET_ALREADY_USED
    message = 'Этот билет уже использован.'
    http_status = status.HTTP_409_CONFLICT


class TicketCancelledError(DomainError):
    code = error_codes.TICKET_CANCELLED
    message = 'Этот билет был отменен.'
    http_status = status.HTTP_409_CONFLICT


class CheckInClosedError(DomainError):
    code = error_codes.CHECKIN_CLOSED
    message = 'Вход на мероприятие пока что закрыт.'
    http_status = status.HTTP_409_CONFLICT


def ticket_use(*, ticket_id: str) -> Ticket:
    '''
    Сервис для использования билета.
    '''

    with transaction.atomic():
        ticket = (
            Ticket.objects
            .select_for_update()
            .select_related('event')
            .filter(pk=ticket_id)
            .first()
        )
        if ticket is None:
            raise exceptions.NotFound('Билета не существует.')

        if ticket.status == TicketStatus.CANCELLED:
            raise TicketCancelledError
        elif ticket.status == TicketStatus.USED:
            raise TicketAlreadyUsedError
        elif ticket.status == TicketStatus.VALID:
            event = ticket.event

            if (
                event.start_at - timedelta(minutes=Ticket.CHECKIN_OPENS_BEFORE_MINUTES) 
                > timezone.now()
            ):
                raise CheckInClosedError

            ticket.status = TicketStatus.USED
            ticket.used_at = timezone.now()
            ticket.save(update_fields=['status', 'used_at'])
            
    return ticket