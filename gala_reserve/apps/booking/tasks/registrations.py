from smtplib import SMTPException

from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string

from apps.booking.models import Registration


@shared_task(
    autoretry_for=(OSError, SMTPException),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=5,
)
def send_registration_cancelled_email(registration_id: int) -> None:
    registration = Registration.objects.select_related(
        'user',
        'event__category',
        'event__user',
        'ticket',
    ).get(pk=registration_id)

    ticket = registration.ticket
    event = registration.event

    context = {
        'registration': registration,
        'ticket': ticket,
        'event': event
    }

    text_body = (
        f'Здравствуйте, {registration.user.first_name or registration.user.username}!\n\n'
        f'Ваша регистрация на мероприятие «{event.title}» отменена. '
        'Билет аннулирован и больше не подходит для прохода на мероприятие.\n\n'
        f'Дата отмены: {registration.cancelled_at:%d.%m.%Y, %H:%M}\n'
        f'Мероприятие: {event.title}\n'
        f'Начало: {event.start_at:%d.%m.%Y, %H:%M}\n'
        f'Адрес: {event.address}\n'
        f'Идентификатор билета: {ticket.pk}\n'
    )

    html_body = render_to_string('emails/registration_cancelled.html', context)

    send_mail(
        subject='GalaReserve - Отмена регистрации',
        message=text_body,
        from_email=None,
        recipient_list=[registration.user.email],
        html_message=html_body,
    )

