from django.db.models import Count, Q
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListCreateAPIView, RetrieveDestroyAPIView
from rest_framework.mixins import UpdateModelMixin
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from apps.events.models import Category, EventStatus
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
        responses={
            200: CategoryOutputSerializer(many=True),
            400: OpenApiResponse(description='Неправильные значения query-параметра(ов)')
        }
    ),
    post=extend_schema(
        tags=['Categories'],
        summary='Создать категорию',
        description='Создает категорию',
        request=CategoryInputSerializer,
        responses={
            201: CategoryOutputSerializer,
            400: OpenApiResponse(description='Ошибка валидации'),
            401: OpenApiResponse(description='Неверный аутентификационный токен'),
            403: OpenApiResponse(description='Требуется верифицированный пользователь')
        },
        examples=[
            OpenApiExample(
                'Пример запроса',
                value={
                    'name': 'Концерты',
                    'description': 'Организация встреч с выступлениями'
                },
                request_only=True
            )
        ]
    )
)
class ListCreateCategoryView(ListCreateAPIView):
    '''
    Представление для получения списка категорий или создания
    категории.
    '''

    queryset = Category.objects.annotate(
        events_count=Count('events', filter=~Q(events__status=EventStatus.DRAFT))
    ).order_by('id')
    filter_backends = (SearchFilter,)
    search_fields = ('name',)

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        elif self.request.method == 'POST':
            return [IsVerified()]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CategoryOutputSerializer
        elif self.request.method == 'POST':
            return CategoryInputSerializer

    def post(self, request: Request, *args, **kwargs) -> Response:
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        instance = input_serializer.save()
        instance = self.get_queryset().get(pk=instance.pk)

        output_serializer = CategoryOutputSerializer(instance=instance)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        tags=['Categories'],
        summary='Получить данные категории',
        description='Извлекает данные о категории по её ID',
        responses={
            200: CategoryOutputSerializer,
            404: OpenApiResponse(description='Категории не существует')
        }
    ),
    patch=extend_schema(
        tags=['Categories'],
        summary='Обновить данные категории',
        description='Обновляет категорию по её ID',
        request=CategoryInputSerializer,
        responses={
            200: CategoryOutputSerializer,
            400: OpenApiResponse(description='Ошибка валидации'),
            401: OpenApiResponse(description='Неверный аутентификационный токен'),
            403: OpenApiResponse(description='Требуется владелец категории или администратор'),
            404: OpenApiResponse(description='Категории не существует')
        },
        examples=[
            OpenApiExample(
                'Пример запроса',
                value={
                    'name': 'Концерты (крупные)',
                    'description': 'Организация крупных концертов'
                },
                request_only=True
            )
        ]
    ),
    delete=extend_schema(
        tags=['Categories'],
        summary='Удалить категорию',
        description='Удаляет категорию по её ID',
        responses={
            204: OpenApiResponse(),
            401: OpenApiResponse(description='Неверный аутентификационный токен'),
            403: OpenApiResponse(description='Требуется владелец категории или администратор'),
            404: OpenApiResponse(description='Категории не существует')
        }
    )
)
class RetrieveUpdateDeleteCategoryView(RetrieveDestroyAPIView, UpdateModelMixin):
    '''
    Представление для извлечения, частичного изменения или удаления
    категории по её ID.
    '''

    queryset = Category.objects.annotate(
        events_count=Count('events', filter=~Q(events__status=EventStatus.DRAFT))
    )
    lookup_url_kwarg = 'id'

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return CategoryOutputSerializer
        elif self.request.method == 'PATCH':
            return CategoryInputSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
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