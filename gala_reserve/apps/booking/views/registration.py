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

from apps.booking.models import Registration
from apps.booking.services.registrations import registration_cancel
from apps.core.serializers import MessageOutputSerializer
from apps.users.permissions import IsOwnerOrAdmin


@extend_schema_view(
    post=extend_schema(
        tags=['Registrations'],
        summary='Отменить регистрацию на мероприятие',
        description='Отменяет регистрацию и билет на мероприятие.',
        request=OpenApiRequest(),
        responses={
            200: MessageOutputSerializer,
            401: OpenApiResponse(description='Неверный или истекший access-токен'),
            403: OpenApiResponse(description='Требуется владелец или администратор'),
            404: OpenApiResponse(description='Регистрации не существует'),
            409: OpenApiResponse(description='Регистрация неактивна / Срок отмены регистрации прошел / '
                                            'Билет регистрации уже использован')
        }
    )
)
class CancelRegistrationView(GenericAPIView):
    '''
    Представление для отмены регистрации и билета на мероприятие.
    '''

    serializer_class = MessageOutputSerializer
    queryset = Registration.objects.all()
    permission_classes = (IsOwnerOrAdmin,)
    lookup_url_kwarg = 'id'

    def post(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()

        registration_cancel(reg_id=instance.pk)

        return Response({
            'message': 'Регистрация на мероприятие отменена. На ваш email было отправлено письмо.'
        }, status=status.HTTP_200_OK)