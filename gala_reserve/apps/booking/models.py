import uuid

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

    CANCEL_DEADLINE_HOURS = 24

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
        ordering = ('id',)
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


class TicketStatus(models.TextChoices):
    VALID = 'valid', 'Действительный'
    USED = 'used', 'Использованный'
    CANCELLED = 'Недействительный'

class Ticket(models.Model):
    '''
    Модель билета.
    '''

    id = models.UUIDField(
        'UUID билета', 
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    registration = models.OneToOneField(Registration, models.PROTECT, related_name='ticket')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT, related_name='users')
    event = models.ForeignKey(Event, models.PROTECT, related_name='tickets')
    status = models.CharField(
        'Статус', 
        max_length=50, 
        choices=TicketStatus.choices, 
        default=TicketStatus.VALID,
        blank=True
    )
    created_at = models.DateTimeField('Дата и время создания', auto_now_add=True, editable=False)
    used_at = models.DateTimeField('Дата и время использования', null=True, blank=True)

    def __repr__(self):
        return f'<Ticket (user={self.user_id}, registration={self.registration_id})>'

    def __str__(self):
        return f'Билет {self.id} ({self.get_status_display().lower()})'

    class Meta:
        verbose_name = 'Билет'
        verbose_name_plural = 'Билеты'
        indexes = (
            Index(
                fields=['user', 'status'],
                name='ticket_user_status_idx'
            ),
            Index(
                fields=['event', 'status'],
                name='ticket_event_status_idx'
            )
        )