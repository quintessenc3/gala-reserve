from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import exceptions, status

from apps.booking.models import (
    Registration,
    RegistrationCancelReason,
    RegistrationStatus,
    Ticket,
    TicketStatus,
)
from apps.booking.tasks.registrations import send_registration_cancelled_email
from apps.core import error_codes
from apps.core.exceptions import DomainError


class RegistrationNotActiveError(DomainError):
    code = error_codes.REGISTRATION_NOT_ACTIVE
    message = 'Эта регистрация уже неактивная.'
    http_status = status.HTTP_409_CONFLICT


class CancellationDeadlinePassed(DomainError):
    code = error_codes.CANCELLATION_DEADLINE_PASSED
    message = 'Срок отмены регистрации на мероприятия прошел.'
    http_status = status.HTTP_409_CONFLICT


class TicketAlreadyUsedError(DomainError):
    code = error_codes.TICKET_ALREADY_USED
    message = 'Билет этой регистрации уже использован.'
    http_status = status.HTTP_409_CONFLICT


def registration_cancel(*, reg_id: int) -> Registration:
    '''
    Сервис отмены регистрации на мероприятие.
    '''

    with transaction.atomic():
        reg = (
            Registration.objects
            .select_for_update(of=('self', 'event'))
            .select_related('event')
            .filter(pk=reg_id)
            .first()
        )
        if reg is None:
            raise exceptions.NotFound(detail='Регистрации не существует.')

        event = reg.event

        if reg.status == RegistrationStatus.CONFIRMED:
            if timezone.now() > event.start_at - timedelta(hours=Registration.CANCEL_DEADLINE_HOURS):
                raise CancellationDeadlinePassed
        elif reg.status == RegistrationStatus.CANCELLED:
            raise RegistrationNotActiveError

        ticket = Ticket.objects.select_for_update().get(registration=reg)

        if ticket.status == TicketStatus.USED:
            raise TicketAlreadyUsedError

        reg.status = RegistrationStatus.CANCELLED
        reg.cancel_reason = RegistrationCancelReason.BY_USER
        reg.cancelled_at = timezone.now()
        reg.save(update_fields=['status', 'cancel_reason', 'cancelled_at'])

        ticket.status = TicketStatus.CANCELLED
        ticket.save(update_fields=['status'])

        event.seats_taken = event.seats_taken - 1
        event.save(update_fields=['seats_taken', 'updated_at'])

        transaction.on_commit(
            lambda: send_registration_cancelled_email.delay(reg.pk)
        )

    return reg