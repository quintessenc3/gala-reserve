from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListCreateAPIView, RetrieveDestroyAPIView
from rest_framework.mixins import UpdateModelMixin
from rest_framework.request import Request
from rest_framework.response import Response

from apps.events.models import Category
from apps.events.serializers.categories import (
    CategoryInputSerializer,
    CategoryOutputSerializer,
)
from apps.events.services.categories import category_delete
from apps.users.permissions import IsOwnerOrAdmin, IsVerified


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
        request=CategoryInputSerializer
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
            return CategoryInputSerializer


@extend_schema_view(
    get=extend_schema(
        tags=['Categories'],
        summary='Получить данные категории',
        description='Извлекает данные о категории по её ID',
        responses={
            200: CategoryOutputSerializer
        }
    ),
    patch=extend_schema(
        tags=['Categories'],
        summary='Обновить данные категории',
        description='Обновляет категорию по её ID',
        request=CategoryInputSerializer,
        responses={
            200: CategoryOutputSerializer,
            400: OpenApiResponse(description='Ошибка валидации')
        }
    ),
    delete=extend_schema(
        tags=['Categories'],
        summary='Удалить категорию',
        description='Удаляет категорию по её ID'
    )
)
class RetrieveUpdateDeleteCategoryView(RetrieveDestroyAPIView, UpdateModelMixin):
    '''
    Представление для извлечения, частичного изменения или удаления
    категории по её ID.
    '''

    serializer_class = CategoryInputSerializer
    queryset = Category.objects.all()
    lookup_url_kwarg = 'id'

    def get_permissions(self):
        if self.request.method == 'GET':
            return []
        elif self.request.method in ('PATCH', 'DELETE'):
            return [IsOwnerOrAdmin()]

    def patch(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()
        input_serializer = self.get_serializer(data=request.data, instance=instance, partial=True)
        input_serializer.is_valid(raise_exception=True)
        input_serializer.save()

        output_serializer = CategoryOutputSerializer(instance=instance)

        return Response(output_serializer.data, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        category_delete(category_id=instance.pk)