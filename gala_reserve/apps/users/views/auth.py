import random

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.generics import CreateAPIView, GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.views import TokenBlacklistView as _TokenBlacklistView
from rest_framework_simplejwt.views import TokenObtainPairView as _TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView as _TokenRefreshView

from apps.core.serializers import MessageOutputSerializer
from apps.users.models import OneTimeCode
from apps.users.serializers.auth import (
    EmailVerifyInputSerializer,
    PasswordResetByCodeInputSerializer,
    RegisterInputSerializer,
    RegisterOutputSerializer,
    RequestEmailResetCodeInputSerializer,
)
from apps.users.services.auth import (
    otp_resend,
    user_email_verify,
    user_register,
    user_request_password_reset_code,
    user_reset_password_by_code,
)
from apps.users.throttles import RegisterAnonThrottle


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
    throttle_classes = (RegisterAnonThrottle,)

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

@extend_schema_view(
    post=extend_schema(
        tags=['Auth'],
        summary='Верифицировать пользователя по коду',
        description='Верифицирует пользователя по коду, присланного на его email.',
        request=EmailVerifyInputSerializer,
        responses={
            200: MessageOutputSerializer,
            400: OpenApiResponse(description='Код неверный / истек / превышен лимит попыток'),
            404: OpenApiResponse(description='Пользователь не найден'),
            409: OpenApiResponse(description='Пользователь уже верифицирован')
        },
        examples=[
            OpenApiExample(
                name='Пример запроса',
                value={
                    'code': ''.join(random.choices('0123456789', k=OneTimeCode.CODE_LENGTH))
                },
                request_only=True
            )
        ]
    )
)
class EmailVerifyView(GenericAPIView):
    '''
    Представление для верификации email пользователя по коду.
    '''

    serializer_class = EmailVerifyInputSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_email_verify(user_id=request.user.pk, **serializer.validated_data)

        return Response({'message': 'Email успешно верифицирован'}, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        tags=['Auth'],
        summary='Повторно отправить код на электронную почту',
        description='Повторно отправляет верификационный код на электронную почту.',
        responses={
            200: MessageOutputSerializer,
            404: OpenApiResponse(description='Пользователь не найден')
        }
    )
)
class CodeResendView(GenericAPIView):
    '''
    Представление для повторной отправки письма с верификационным кодом.
    '''

    def get(self, request: Request, *args, **kwargs) -> Response:
        otp_resend(user_id=request.user.pk)

        return Response({'message': 'Код был повторно выслан на электронную почту'}, status=status.HTTP_200_OK)


@extend_schema_view(
    post=extend_schema(
        tags=['Auth'],
        summary='Добавить refresh-токен в черный список',
        description='Добавляет refresh-токен в черный список.',
        responses={
            204: OpenApiResponse(description='Токен добавлен в черный список'),
            401: OpenApiResponse(description='Неверный аутентификационный токен')
        }
    )
)
class LogoutView(_TokenBlacklistView):
    '''
    Представление для добавления refresh-токена в черный список.
    '''

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0]) from e

        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    post=extend_schema(
        tags=['Auth'],
        summary='Запросить код сброса пароля',
        description='Отправляет код сброса пароля на электронную почту пользователя.',
        request=RequestEmailResetCodeInputSerializer,
        responses={
            202: MessageOutputSerializer
        }
    )
)
class RequestResetCodeView(GenericAPIView):
    '''
    Представление для запроса сброса кода.
    '''

    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = RequestEmailResetCodeInputSerializer

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_request_password_reset_code(**serializer.validated_data)

        return Response({'message': 'Код сброса пароля был отправлен на ваш email'}, status=status.HTTP_202_ACCEPTED)


@extend_schema_view(
    post=extend_schema(
        tags=['Auth'],
        summary='Сбросить пароль по коду',
        description='Сбрасывает пароль пользователя по коду, присланному на его email.',
        request=PasswordResetByCodeInputSerializer,
        responses={
            200: MessageOutputSerializer,
            400: OpenApiResponse(description='Код неверный / истек / превышен лимит попыток')
        }
    )
)
class PasswordResetByCodeView(GenericAPIView):
    '''
    Представление для сброса пароля по коду.
    '''

    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = PasswordResetByCodeInputSerializer

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_reset_password_by_code(**serializer.validated_data)

        return Response({'message': 'Пароль успешно сброшен'}, status=status.HTTP_200_OK)