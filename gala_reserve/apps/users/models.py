from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone


class User(AbstractUser):
    '''
    Модель пользователя.
    '''

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username',)
    PHOTO_DIRECTORY = Path('users', 'photos')
    DEFAULT_PHOTO = PHOTO_DIRECTORY / 'default_avatar.webp'
    MIN_USERNAME_LENGTH = 3
    MAX_USERNAME_LENGTH = 30
    MAX_PHOTO_FILE_SIZE_BYTES = 2 * 1024 * 1024
    MAX_PHOTO_RESOLUTION = (4096, 4096)
    THUMBNAIL_SIZE_PX = (512, 512)

    username = models.CharField(
        'Имя пользователя',
        max_length=MAX_USERNAME_LENGTH,
        validators=[
            RegexValidator(f'[A-Za-z0-9_]{{{MIN_USERNAME_LENGTH},{MAX_USERNAME_LENGTH}}}')
        ],
    )
    email = models.EmailField('Электронная почта', unique=True)
    first_name = models.CharField('Имя', max_length=50, blank=True)
    last_name = models.CharField('Фамилия', max_length=50, blank=True)
    bio = models.CharField('О себе', max_length=500, blank=True)
    photo = models.ImageField('Фото профиля', upload_to=PHOTO_DIRECTORY, default=str(DEFAULT_PHOTO), null=True, blank=True)
    is_email_verified = models.BooleanField('Электронная почта верифицирована?', default=False)

    def __repr__(self):
        return f'<User {self.pk} (username={self.username}, email={self.email})>'

    def __str__(self):
        return f'Пользователь {self.username}'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        constraints = (
            models.UniqueConstraint(
                Lower('email'),
                name='unique_user_email',
                violation_error_message='Пользователь с такой электронной почтой уже существует.'
            ),
            models.UniqueConstraint(
                Lower('username'),
                name='unique_user_username',
                violation_error_message='Пользователь с таким именем пользователя уже существует.'
            ),
        )


class OneTimeCodePurpose(models.TextChoices):
    EMAIL_VERIFICATION = 'email_verification', 'Верификация email'
    PASSWORD_RESET = 'password_reset', 'Сброс пароля'

class OneTimeCode(models.Model):
    '''
    Модель одноразового кода.
    '''

    TTL_MINUTES = timedelta(minutes=15)
    MAX_ATTEMPTS = 5
    RESEND_COOLDOWN_SECONDS = timedelta(seconds=60)
    CODE_LENGTH = 6
    CODE_REGEX = f'^[0-9]{{{CODE_LENGTH}}}$'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='onetimecodes')
    purpose = models.CharField('Назначение', max_length=32, choices=OneTimeCodePurpose.choices)
    code_hash = models.CharField('Хэш кода', max_length=64)
    attempts = models.PositiveSmallIntegerField('Кол-во попыток', default=0)
    used_at = models.DateTimeField('Дата и время использования', null=True, blank=True)
    created_at = models.DateTimeField('Дата и время создания', default=timezone.now)

    @property
    def is_expired(self):
        return timezone.now() >= self.created_at + self.TTL_MINUTES

    @property
    def is_reached_attempts_limit(self):
        return self.attempts >= OneTimeCode.MAX_ATTEMPTS

    def __repr__(self):
        return f'<OneTimeCode #{self.pk} (user_id={self.user_id}, purpose={self.purpose})>'
    
    def __str__(self):
        return f'Одноразовый код #{self.pk}'

    class Meta:
        verbose_name = 'Одноразовый код'
        verbose_name_plural = 'Одноразовые коды'
        indexes = (
            models.Index(
                fields=['user', 'purpose', '-created_at'],
                name='onetimecode_user_purpose_idx',
            ),
        )
        constraints = (
            models.CheckConstraint(
                condition=Q(purpose__in=OneTimeCodePurpose.values),
                name='otc_valid_purpose_ck',
            ),
        )