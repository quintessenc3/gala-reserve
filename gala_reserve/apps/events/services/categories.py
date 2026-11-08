from django.db.models import ProtectedError
from rest_framework import exceptions, status

from apps.core import error_codes
from apps.core.exceptions import DomainError
from apps.events.models import Category


class CategoryInUseError(DomainError):
    code = error_codes.CATEGORY_IN_USE
    message = 'Нельзя удалить категорию, у которой есть мероприятия.'
    http_status = status.HTTP_409_CONFLICT


def category_delete(*, category_id: int) -> None:
    '''
    Сервис удаления категории.
    '''

    try:
        category = Category.objects.get(pk=category_id)
    except Category.DoesNotExist:
        raise exceptions.NotFound(detail='Категории с таким id не существует.')

    try:
        category.delete()
    except ProtectedError:
        raise CategoryInUseError