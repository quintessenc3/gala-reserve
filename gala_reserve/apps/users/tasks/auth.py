from smtplib import SMTPException

from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string


@shared_task(
    autoretry_for=(OSError, SMTPException),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=5
)
def send_verification_email(recipient_email: str, code: str | int, ttl_minutes: int) -> None:
    context = {'code': code, 'ttl_minutes': ttl_minutes}

    text_body = f'Ваш верификационный код: {code}. Он истекает через {ttl_minutes} минут.'
    html_body = render_to_string('emails/verification_code.html', context)

    send_mail(
        subject='Ваш верификационный код GalaReserve',
        message=text_body,
        from_email=None,
        recipient_list=[recipient_email],
        html_message=html_body
    )


@shared_task(
    autoretry_for=(OSError, SMTPException),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=5
)
def send_password_reset_email(recipient_email: str, code: str | int, ttl_minutes: int) -> None:
    context = {'code': code, 'ttl_minutes': ttl_minutes}

    text_body = f'Ваш код для сброса пароля: {code}. Он истекает через {ttl_minutes} минут.'
    html_body = render_to_string('emails/password_reset.html', context)

    send_mail(
        subject='Сброс пароля GalaReserve',
        message=text_body,
        from_email=None,
        recipient_list=[recipient_email],
        html_message=html_body
    )