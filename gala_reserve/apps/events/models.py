from django.conf import settings
from django.db import models
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