from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.mixins import UpdateModelMixin
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response

from apps.booking.filters import RegistrationFilter, TicketFilter
from apps.booking.models import Registration, Ticket
from apps.booking.selectors import RegistrationSelector, TicketSelector
from apps.booking.serializers.registrations import (
    RegistrationOutputSerializer,
    TicketOutputSerializer,
)
from apps.core.serializers import MessageOutputSerializer
from apps.events.models import Event
from apps.events.selectors import EventSelector
from apps.events.serializers.events import EventOutputSerializer
from apps.users.models import User
from apps.users.permissions import IsVerified
from apps.users.serializers.my_profile import (
    MyProfileOutputSerializer,
    MyProfilePhotoUploadSerializer,
    MyProfileUpdateSerializer,
    PasswordResetByOldPasswordInputSerializer,
)
from apps.users.services.auth import user_reset_password_by_old_password
from apps.users.services.profile import user_set_photo
from apps.users.throttles import PasswordResetUserThrottle


@extend_schema_view(
    get=extend_schema(
        tags=['Users'],
        summary='Получить информацию о своем профиле',
        description='Получает информацию о текущем пользователе, вошедшего в систему.',
        responses={
            200: MyProfileOutputSerializer,
            401: OpenApiResponse(description='Неверный аутентификационный токен')
        }
    ),
    patch=extend_schema(
        tags=['Users'],
        summary='Обновить информацию о своем профиле',
        description='Обновляет информацию о текущем пользователе, вошедшего в систему.',
        responses={
            200: MyProfileUpdateSerializer,
            400: OpenApiResponse(description='Ошибка валидации'),
            401: OpenApiResponse(description='Неверный аутентификационный токен')
        },
        examples=[
            OpenApiExample(
                name='Пример запроса',
                value={
                    "first_name": "Андрей",
                    "last_name": "Волков",
                    "username": "andrey_volkov",
                    "bio": "Уличный фотограф. Люблю архитектуру, ночные прогулки и атмосферу больших городов. Всегда ищу необычные ракурсы и интересные истории."
                },
                request_only=True
            )
        ]
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


@extend_schema_view(
    post=extend_schema(
        tags=['Users'],
        summary='Сбросить пароль по старому паролю',
        description='Сбрасывает пароль текущего пользователя, используя старый пароль для проверки.',
        request=PasswordResetByOldPasswordInputSerializer,
        responses={
            200: MessageOutputSerializer,
            400: OpenApiResponse(description='Ошибка валидации / Старый пароль не совпадает'),
            401: OpenApiResponse(description='Неверный аутентификационный токен'),
            404: OpenApiResponse(description='Пользователь не найден'),
            429: OpenApiResponse(description='Слишком много запросов')
        },
        examples=[
            OpenApiExample(
                name='Пример запроса',
                value={
                    "old_password": "rT8!vN4#qL2@xP7$kM9",
                    "new_password": "C6@zW3!pH8#sR2^mJ5q"
                },
                request_only=True
            )
        ]
    )
)
class PasswordResetByOldPasswordView(GenericAPIView):
    '''
    Представление для сброса пароля по старому паролю.
    '''

    serializer_class = PasswordResetByOldPasswordInputSerializer
    throttle_classes = (PasswordResetUserThrottle,)

    def post(self, request: Request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_reset_password_by_old_password(user_id=request.user.pk, **serializer.validated_data)

        return Response({'message': 'Пароль успешно сброшен'}, status=status.HTTP_200_OK)
    

@extend_schema_view(
    get=extend_schema(
        tags=['Users'],
        summary='Получить список своих мероприятий',
        description='Получает список своих мероприятий любого статуса.',
        responses={
            200: EventOutputSerializer(many=True),
            401: OpenApiResponse(description='Неверный аутентификационный токен'),
            403: OpenApiResponse(description='Требуется верифицированный пользователь')
        }
    )
)
class MyEventsView(ListAPIView):
    '''
    Представление для просмотра своих мероприятий.
    '''

    queryset = Event.objects.none()
    serializer_class = EventOutputSerializer
    permission_classes = (IsVerified,)

    def get_queryset(self):
        return EventSelector.my_events(viewer=self.request.user)


@extend_schema_view(
    get=extend_schema(
        tags=['Users'],
        summary='Получить список своих регистраций на мероприятия',
        description='Получает список своих регистраций на мероприятия.',
        responses={
            200: RegistrationOutputSerializer(many=True),
            401: OpenApiResponse(description='Неверный аутентификационный токен')
        }
    )
)
class MyRegistrationsView(ListAPIView):
    '''
    Представление для просмотра своих регистраций на мероприятия.
    '''

    queryset = Registration.objects.none()
    serializer_class = RegistrationOutputSerializer
    filterset_class = RegistrationFilter
    
    def get_queryset(self):
        return (
            RegistrationSelector
            .my_registrations(viewer=self.request.user)
            .select_related('event')
        )


@extend_schema_view(
    get=extend_schema(
        tags=['Users'],
        summary='Получить список своих билетов на мероприятия',
        description='Получает список своих билетов на мероприятия.',
        responses={
            200: TicketOutputSerializer(many=True),
            401: OpenApiResponse(description='Неверный или истекший access-токен')
        }
    )
)
class MyTicketsView(ListAPIView):
    '''
    Представление для просмотра своих билетов.
    '''

    queryset = Ticket.objects.none()
    serializer_class = TicketOutputSerializer
    filterset_class = TicketFilter

    def get_queryset(self):
        return (
            TicketSelector
            .my_tickets(viewer=self.request.user)
            .select_related('event')
        )


@extend_schema_view(
    put=extend_schema(
        tags=['Users'],
        summary='Обновить фотографию профиля',
        description='Обновляет фотографию профиля.',
        request=MyProfilePhotoUploadSerializer,
        responses={
            200: MyProfileOutputSerializer,
            400: OpenApiResponse(description='Ошибка валидации / Файл не является корректным изображением / Недопустимый формат / '
                                 'Слишком большой / Слишком широкий или высокий'),
            401: OpenApiResponse(description='Неверный аутентификационный токен'),
            404: OpenApiResponse(description='Пользователя не существует')
        }
    )
)
class MyProfileUploadPhotoView(GenericAPIView):
    '''
    Представление для загрузки фотографии профиля.
    '''

    serializer_class = MyProfilePhotoUploadSerializer
    parser_classes = (MultiPartParser,)

    def put(self, request: Request, *args, **kwargs) -> Response:
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        user = user_set_photo(user_id=request.user.pk, **input_serializer.validated_data)

        output_serializer = MyProfileOutputSerializer(instance=user)
        return Response(output_serializer.data, status=status.HTTP_200_OK)