from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import CheckConstraint, F, Q
from django.db.models.functions import Lower


class Category(models.Model):
    '''
    Модель категории события.
    '''

    name = models.CharField('Название категории', max_length=100)
    description = models.TextField('Описание категории')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_categories'
    )
    created_at = models.DateTimeField('Дата и время создания', auto_now_add=True)

    class Meta:
        verbose_name = 'Категория события'
        verbose_name_plural = 'Категории событий'
        constraints = (
            models.UniqueConstraint(
                Lower('name'),
                name='unique_category_name',
                violation_error_message='Категория с таким названием уже существует.'
            ),
        )


class EventStatus(models.TextChoices):
    DRAFT = 'draft', 'Черновик'
    PUBLISHED = 'published', 'Опубликовано'
    COMPLETED = 'completed', 'Проведено'
    CANCELLED = 'cancelled', 'Отменено'

class Event(models.Model):
    '''
    Модель мероприятия.
    '''

    IMAGE_DIRECTORY = Path('events', 'images')

    title = models.CharField('Название', max_length=200)
    description = models.TextField('Описание')
    category = models.ForeignKey(Category, models.PROTECT, related_name='events')
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT, related_name='events')
    image = models.ImageField('Изображение', upload_to=IMAGE_DIRECTORY, null=True, blank=True)
    address = models.CharField('Адрес проведения', max_length=255)
    start_at = models.DateTimeField('Дата и время начала')
    end_at = models.DateTimeField('Дата и время окончания')
    capacity = models.PositiveIntegerField(
        'Вместимость',
        validators=[
            MinValueValidator(1, message='Минимальная Вместимость - 1.'),
            MaxValueValidator(100_000, message='Максимальная Вместимость - 100 000.')
        ]
    )
    seats_taken = models.PositiveIntegerField('Кол-во активных регистраций', default=0, editable=False)
    price = models.DecimalField(
        'Цена билета', 
        max_digits=10, 
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal('0.00'), message='Минимальная цена билета - 0.00 рублей.'),
            MaxValueValidator(Decimal('99999999.99'), message='Максимальная цена билета - 99999999.99 рублей.')
        ]
    )
    status = models.CharField('Статус', max_length=50, choices=EventStatus.choices)
    created_at = models.DateTimeField('Дата и время создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата и время обновления', auto_now=True)
    published_at = models.DateTimeField('Дата и время публикации', null=True, blank=True)

    class Meta:
        verbose_name = 'Мероприятие'
        verbose_name_plural = 'Мероприятия'
        constraints = (
            CheckConstraint(
                condition=Q(capacity__gte=F('seats_taken')),
                name='event_capacity_gte_seats_taken',
                violation_error_message='Кол-во свободных мест не может быть меньше кол-ва активных регистраций.'
            ),
            CheckConstraint(
                condition=Q(price__gte=Decimal('0.00'), price__lte=Decimal('99999999.99')),
                name='event_price_gte_0',
                violation_error_message='Цена не может быть ниже 0.00 или больше 99999999.99.'
            ),
            CheckConstraint(
                condition=Q(capacity__gte=1, capacity__lte=100_000),
                name='event_capacity_gte_1_lte_100000',
                violation_error_message='Вместимость может быть только числом в диапазоне от 1 до 100 000.'
            ),
            CheckConstraint(
                condition=Q(end_at__gt=F('start_at')),
                name='event_end_at_gt_start_at',
                violation_error_message='Дата и время окончания не может быть раньше или равно дате и времени начала мероприятия.'
            ),
            CheckConstraint(
                condition=Q(status__in=EventStatus.values),
                name='event_status_in_allowed_statuses',
                violation_error_message='Такого статуса мероприятия не существует.'
            ),
            CheckConstraint(
                condition=(
                    Q(status=EventStatus.DRAFT, published_at__isnull=True) | (
                        ~Q(status=EventStatus.DRAFT) & Q(published_at__isnull=False)
                    )),
                name='event_published_at_matches_status',
                violation_error_message='Дата публикации должна быть пустой у черновика и заполненной при других статусах.',
            )
        )