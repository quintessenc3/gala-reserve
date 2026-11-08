from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListCreateAPIView

from apps.events.models import Category
from apps.events.serializers.categories import (
    CategoryCreateSerializer,
    CategoryOutputSerializer,
)
from apps.users.permissions import IsVerified


@extend_schema_view(
    get=extend_schema(
        tags=['Categories'],
        summary='Получить список категорий',
        description='Возвращает список категорий',
        request=CategoryOutputSerializer
    ),
    post=extend_schema(
        tags=['Categories'],
        summary='Создать категорию',
        description='Создает категорию',
        request=CategoryCreateSerializer
    )
)
class ListCreateCategoryView(ListCreateAPIView):
    '''
    Представление для получения списка категорий или создания
    категории.
    '''

    queryset = Category.objects.all()
    filter_backends = (SearchFilter,)
    search_fields = ('name',)

    def get_permissions(self):
        if self.request.method == 'GET':
            return []
        elif self.request.method == 'POST':
            return [IsVerified()]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CategoryOutputSerializer
        elif self.request.method == 'POST':
            return CategoryCreateSerializer