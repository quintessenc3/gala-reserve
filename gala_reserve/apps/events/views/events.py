from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListCreateAPIView
from rest_framework.request import Request
from rest_framework.response import Response

from apps.events.selectors import EventSelector
from apps.events.serializers.events import EventCreateSerializer, EventOutputSerializer
from apps.users.permissions import IsVerified


@extend_schema_view(
    get=extend_schema(
        tags=['Events'],
        summary='Получить список опубликованных мероприятий',
        description='Получает список всех опубликованных мероприятий, не находящихся в статусе черновика.',
    ),
    post=extend_schema(
        tags=['Events'],
        summary='Создать черновик мероприятия',
        description='Создает мероприятие в статусе черновика.',
        request=EventCreateSerializer,
        responses={
            201: EventOutputSerializer,
            400: OpenApiResponse(description='Ошибка валидации')
        },
    )
)
class ListCreateEventView(ListCreateAPIView):
    '''
    Представление для получения списка любых опубликованных мероприятий 
    или создания мероприятия.
    '''

    queryset = EventSelector.public_events()
    filter_backends = (SearchFilter,)
    search_fields = ('title', 'description', 'address')
    

    def get_authenticators(self):
        request = getattr(self, 'request', None)
        if request is not None and request.method == 'GET':
            return []
        
        return super().get_authenticators()

    def get_permissions(self):
        if self.request.method == 'GET':
            return []

        return [IsVerified()]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return EventOutputSerializer
        elif self.request.method == 'POST':
            return EventCreateSerializer

    def post(self, request: Request, *args, **kwargs) -> Response:
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        input_serializer.save()

        output_serializer = EventOutputSerializer(instance=input_serializer.instance)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)