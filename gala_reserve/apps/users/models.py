from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from pathlib import Path


class User(AbstractUser):
    '''
    Модель пользователя.
    '''

    USERNAME_FIELD = 'email'
    PHOTO_DIRECTORY = Path('users', 'photos')

    username = models.CharField(
        max_length=30,
        validators=[
            MinValueValidator(3),
            RegexValidator('[A-Za-z0-9_]')
        ]
    )
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    bio = models.CharField(max_length=500, blank=True)
    photo = models.ImageField(upload_to=PHOTO_DIRECTORY, null=True)
    is_email_verified = models.BooleanField(default=False)

    def __repr__(self):
        return f'<User {self.pk} (username={self.username}, email={self.email})>'

    def __str__(self):
        return f'Пользователь {self.username}'

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        
