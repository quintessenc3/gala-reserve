from django.conf import settings
from django.db import models
from django.db.models import Index, Q, UniqueConstraint

from apps.events.models import Event


class RegistrationStatus(models.TextChoices):
    PENDING = 'pending', 'В обработке'
    CONFIRMED = 'confirmed', 'Подтверждена'
    CANCELLED = 'cancelled', 'Отменена'

class RegistrationCancelReason(models.TextChoices):
    BY_USER = 'by_user', 'Отменена пользователем'
    PAYMENT_EXPIRED = 'payment_expired', 'Истек срок оплаты'
    EVENT_CANCELLED = 'event_cancelled', 'Мероприятие отменилось'

class Registration(models.Model):
    '''
    Модель регистрации на бесплатное мероприятие.
    '''

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='registrations',
        db_index=False
    )
    event = models.ForeignKey(
        Event, 
        on_delete=models.PROTECT, 
        related_name='registrations',
        db_index=False
    )
    status = models.CharField(
        'Статус', 
        max_length=50, 
        choices=RegistrationStatus.choices, 
        default=RegistrationStatus.PENDING
    )
    cancel_reason = models.CharField(
        'Причина отмены', 
        max_length=50, 
        choices=RegistrationCancelReason.choices, 
        blank=True
    )
    created_at = models.DateTimeField('Дата и время создания', auto_now_add=True, editable=False)
    confirmed_at = models.DateTimeField('Дата и время подтверждения', null=True, blank=True)
    cancelled_at = models.DateTimeField('Дата и время отмены', null=True, blank=True)

    class Meta:
        verbose_name = 'Регистрация'
        verbose_name_plural = 'Регистрации'
        constraints = (
            UniqueConstraint(
                fields=['user', 'event'],
                condition=Q(status__in=[RegistrationStatus.PENDING, RegistrationStatus.CONFIRMED]),
                name='reg_active_user_event_uidx'
            ),
        )
        indexes = (
            Index(
                fields=['event', 'status'],
                name='reg_event_status_idx'
            ),
            Index(
                fields=['user', 'status', '-created_at'],
                name='reg_status_desc_created_at_idx'
            )
        )