from drf_spectacular.utils import (
    OpenApiRequest,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.serializers import MessageOutputSerializer
from apps.events.selectors import EventSelector
from apps.events.services.booking import book_free_event
from apps.users.permissions import IsVerified


@extend_schema_view(
    post=extend_schema(
        tags=['Events'],
        summary='Записаться на бесплатное мероприятие',
        description='Записывает пользователя на бесплатное мероприятие и отправляет'
                    'ему на почту письмо с билетом.',
        request=OpenApiRequest(),
        responses={
            200: MessageOutputSerializer,
            400: OpenApiResponse(description='Ошибка валидации'),
            401: OpenApiResponse(description='Неверный аутентификационный токен'),
            403: OpenApiResponse(description='Требуется верифицированный пользователь'),
            404: OpenApiResponse(description='Мероприятия или пользователя не существует'),
            409: OpenApiResponse(description='Мероприятие не опубликовано / Мероприятие платное / '
                                            'Регистрация закрыта / Нет свободных мест / Уже зарегистрирован')
        }
    )
)
class RegisterFreeEventView(GenericAPIView):
    '''
    Представление для регистрации на бесплатное мероприятие.
    '''

    serializer_class = MessageOutputSerializer
    queryset = EventSelector.public_events()
    permission_classes = (IsVerified,)
    lookup_url_kwarg = 'id'

    def post(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()

        book_free_event(event_id=instance.pk, user_id=request.user.pk)

        return Response({
            'message': 'Регистрация прошла успешно. На ваш email был отправлен билет.'
        }, status=status.HTTP_200_OK)