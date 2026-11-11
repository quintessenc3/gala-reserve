from decimal import Decimal
from smtplib import SMTPException

from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string

from apps.booking.models import Ticket


@shared_task(
    autoretry_for=(OSError, SMTPException),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=5
)
def send_ticket_email(ticket_id: str) -> None:
    ticket = Ticket.objects.select_related(
        'user',
        'event__category',
        'event__user',
    ).get(pk=ticket_id)

    context = {
        'ticket': ticket,
        'is_free': ticket.event.price == Decimal('0.00'),
    }

    text_body = (
        f'Ваш билет на мероприятие «{ticket.event.title}» готов.\n'
        f'Идентификатор билета: {ticket.pk}\n'
        f'Адрес: {ticket.event.address}'
    )

    html_body = render_to_string(
        'emails/ticket.html',
        context
    )

    send_mail(
        subject='GalaReserve - Ваш билет на мероприятие',
        message=text_body,
        from_email=None,
        recipient_list=[ticket.user.email],
        html_message=html_body
    )