from smtplib import SMTPException

from celery import shared_task
from django.core.mail import send_mail


@shared_task(
    autoretry_for=(OSError, SMTPException),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=5
)
def send_verification_email(recipient_email: str, code: str | int, ttl_minutes: int) -> None:
    send_mail(
        subject='Ваш верификационный код GalaReserve',
        message=f'Ваш верификационный код: {code}. Он истекает через {ttl_minutes} минут.',
        from_email=None,
        recipient_list=[recipient_email]
    )