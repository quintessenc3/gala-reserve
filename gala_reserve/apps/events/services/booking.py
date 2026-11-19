from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import exceptions, status

from apps.booking.models import Registration, RegistrationStatus, Ticket
from apps.core import error_codes
from apps.core.exceptions import DomainError
from apps.events.models import Event, EventStatus
from apps.events.tasks.booking import send_ticket_email
from apps.users.models import User


class EventNotPublishedError(DomainError):
    code = error_codes.EVENT_NOT_PUBLISHED
    message = 'Нельзя записаться на это мероприятие, так как оно не опубликовано.'
    http_status = status.HTTP_409_CONFLICT


class RegistrationClosedError(DomainError):
    code = error_codes.REGISTRATION_CLOSED
    message = 'Нельзя записаться на это мероприятие, так как регистрация на него уже закрыта.'
    http_status = status.HTTP_409_CONFLICT


class AlreadyRegisteredError(DomainError):
    code = error_codes.ALREADY_REGISTERED
    message = 'Вы уже записаны на это мероприятие.'
    http_status = status.HTTP_409_CONFLICT


class NoSeatsAvailableError(DomainError):
    code = error_codes.NO_SEATS_AVAILABLE
    message = 'На это мероприятие закончились свободные места.'
    http_status = status.HTTP_409_CONFLICT


class PaymentRequiredError(DomainError):
    code = error_codes.PAYMENT_REQUIRED
    message = 'Для регистрации на это мероприятие требуется оплата.'
    http_status = status.HTTP_409_CONFLICT


class EventIsFreeError(DomainError):
    code = error_codes.EVENT_IS_FREE
    message = 'Это бесплатное мероприятие, и оно не требует оплаты.'
    http_status = status.HTTP_409_CONFLICT


def _try_register(*, event_id: int, user_id: int, is_free: bool) -> Registration:
    '''
    Сервис, для валидации доступности мероприятия и создания 
    регистрации.
    '''

    event = Event.objects.select_for_update().filter(pk=event_id).first()
    if event is None:
        raise exceptions.NotFound(detail='Мероприятия не существует.')

    user = User.objects.select_for_update().filter(pk=user_id).first()
    if user is None:
        raise exceptions.NotFound(detail='Пользователя не существует.') 

    if is_free == True and event.price > 0:
        raise PaymentRequiredError
    elif is_free == False and event.price <= 0:
        raise EventIsFreeError
    
    if event.status != EventStatus.PUBLISHED:
        raise EventNotPublishedError

    if timezone.now() >= event.start_at:
        raise RegistrationClosedError

    if event.capacity - event.seats_taken <= 0:
        raise NoSeatsAvailableError

    try:
        registration = Registration.objects.create(
            user=user,
            event=event
        )
    except IntegrityError:
        raise AlreadyRegisteredError

    return event, user, registration


def book_free_event(*, event_id: int, user_id: int) -> None:
    '''
    Сервис для записи на бесплатное мероприятие.
    '''

    with transaction.atomic():
        event, user, registration = _try_register(event_id=event_id, user_id=user_id)
        
        registration.status = RegistrationStatus.CONFIRMED
        registration.confirmed_at = timezone.now()
        registration.save(update_fields=['status', 'confirmed_at'])
        
        event.seats_taken = event.seats_taken + 1
        event.save(update_fields=['seats_taken', 'updated_at'])

        ticket = Ticket.objects.create(
            registration=registration,
            user=user,
            event=event
        )

        transaction.on_commit(
            lambda: send_ticket_email.delay(ticket_id=ticket.pk)
        )