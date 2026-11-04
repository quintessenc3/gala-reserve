from django.contrib.auth import get_user_model
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers, status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenObtainPairView as _TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView as _TokenRefreshView

from apps.users.serializers.auth import (
    RegisterInputSerializer,
    RegisterOutputSerializer,
)
from apps.users.services.auth import user_register


@extend_schema_view(
    post=extend_schema(
        tags=['Auth'],
        summary='Регистрация пользователя',
        description='Создает учетную запись и отправляет код с верификационным кодом на почту.',
        request=RegisterInputSerializer,
        responses={
            201: RegisterOutputSerializer,
            400: OpenApiResponse(description='Ошибка валидации входных данных'),
        },
        examples=[
            OpenApiExample(
                'Пример запроса',
                value={
                    'email': 'user@example.com',
                    'username': 'User',
                    'password': 'P@ssw0rd',
                    'first_name': 'Иван',
                    'last_name': 'Иванов',
                },
                request_only=True,
            ),
        ]
    )
)
class RegisterView(CreateAPIView):
    '''
    Представление регистрации пользователя.
    '''

    serializer_class = RegisterInputSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        user = user_register(**input_serializer.validated_data)

        output_serializer = RegisterOutputSerializer(instance=user)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    post=extend_schema(
        tags=['Auth'],
        summary='Получить refresh и access токены',
        description='Принимает поле пользователя, используемого в качестве username, и пароль',
        request=TokenObtainPairSerializer,
        responses={
            200: TokenObtainPairSerializer,
            401: OpenApiResponse(description='Неверный код')
        }
    )
)
class TokenObtainPairView(_TokenObtainPairView):
    '''
    Представление для получения refresh и access токенов.
    '''


@extend_schema_view(
    post=extend_schema(
        tags=['Auth'],
        summary='Заменить refresh токен',
        description='Принимает refresh и access токен и возвращает refresh токен',
        request=TokenRefreshSerializer,
        responses={
            201: TokenRefreshSerializer,
            401: OpenApiResponse(description='Неверный код')
        }
    )
)
class TokenRefreshView(_TokenRefreshView):
    '''
    Представление для замены refresh и access токенов по refresh токену.
    '''