from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

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