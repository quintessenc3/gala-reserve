from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework.generics import RetrieveAPIView
from rest_framework.mixins import UpdateModelMixin
from rest_framework.request import Request
from rest_framework.response import Response

from apps.users.models import User
from apps.users.serializers.my_profile import (
    MyProfileOutputSerializer,
    MyProfileUpdateSerializer,
)


@extend_schema_view(
    get=extend_schema(
        tags=['Users'],
        summary='Получить информацию о своем профиле',
        description='Получает информацию о текущем пользователе, вошедшего в систему.',
        responses={
            200: MyProfileOutputSerializer
        }
    ),
    patch=extend_schema(
        tags=['Users'],
        summary='Обновить информацию о своем профиле',
        description='Обновляет информацию о текущем пользователе, вошедшего в систему.',
        responses={
            200: MyProfileUpdateSerializer,
            400: OpenApiResponse(description='Ошибка валидации')
        }
    )
)
class MyProfileView(RetrieveAPIView, UpdateModelMixin):
    '''
    Представление просмотра или изменения информации о своем профиле.
    '''
    
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return MyProfileOutputSerializer
        elif self.request.method == 'PATCH':
            return MyProfileUpdateSerializer

    def get_object(self):
        return self.get_queryset().get(pk=self.request.user.pk)

    def patch(self, request: Request, *args, **kwargs) -> Response:
        return self.partial_update(request, *args, **kwargs)