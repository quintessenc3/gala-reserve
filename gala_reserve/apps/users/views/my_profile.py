from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import GenericAPIView, ListAPIView, RetrieveAPIView
from rest_framework.mixins import UpdateModelMixin
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
    MyProfileUpdateSerializer,
    PasswordResetByOldPasswordInputSerializer,
)
from apps.users.services.auth import user_reset_password_by_old_password
from apps.users.throttles import PasswordResetUserThrottle


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


@extend_schema_view(
    post=extend_schema(
        tags=['Users'],
        summary='Сбросить пароль по старому паролю',
        description='Сбрасывает пароль текущего пользователя, используя старый пароль для проверки.',
        request=PasswordResetByOldPasswordInputSerializer,
        responses={
            200: MessageOutputSerializer,
            400: OpenApiResponse(description='Старый пароль не совпадает'),
            404: OpenApiResponse(description='Пользователь не найден'),
        }
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
        description='Получает список своих мероприятий любого статуса.'
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
        description='Получает список своих регистраций на мероприятия.'
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
            200: TicketOutputSerializer,
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

    