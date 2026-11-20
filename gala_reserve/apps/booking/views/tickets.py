from drf_spectacular.utils import (
    OpenApiRequest,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.booking.permissions import IsTicketEventOwnerOrAdmin
from apps.booking.selectors import TicketSelector
from apps.booking.services.tickets import ticket_use
from apps.core.serializers import MessageOutputSerializer


@extend_schema_view(
    post=extend_schema(
        tags=['Tickets'],
        summary='Использовать билет',
        description='Переводит билет в статус использованного.',
        request=OpenApiRequest(),
        responses={
            200: MessageOutputSerializer,
            401: OpenApiResponse(description='Неверный или истекший access-токен'),
            403: OpenApiResponse(description='Требуется владелец мероприятия или администратор'),
            404: OpenApiResponse(description='Билета не существует'),
            409: OpenApiResponse(description='Билет отменен или использован / Время открытия входа еще не наступило')
        }
    )
)
class TicketUseView(GenericAPIView):
    '''
    Представление использования билета.
    '''

    serializer_class = MessageOutputSerializer
    permission_classes = (IsAuthenticated, IsTicketEventOwnerOrAdmin)
    lookup_url_kwarg = 'id'

    def get_queryset(self):
        return TicketSelector.visible_to(viewer=self.request.user)

    def post(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()

        ticket_use(ticket_id=instance.id)

        return Response({'message': 'Билет успешно использован.'}, status=status.HTTP_200_OK)