from pathlib import Path

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    '''
    Модель пользователя.
    '''

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username',)
    PHOTO_DIRECTORY = Path('users', 'photos')
    MIN_USERNAME_LENGTH = 3
    MAX_USERNAME_LENGTH = 30

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
    photo = models.ImageField('Фото профиля', upload_to=PHOTO_DIRECTORY, null=True, blank=True)
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