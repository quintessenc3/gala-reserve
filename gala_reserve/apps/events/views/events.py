from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiRequest,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.filters import SearchFilter
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.events.filters import EventFilter
from apps.events.models import Event
from apps.events.selectors import EventSelector
from apps.events.serializers.events import (
    EventCreateSerializer,
    EventImageUploadSerializer,
    EventOutputDetailSerializer,
    EventOutputSerializer,
    EventUpdateSerializer,
)
from apps.events.services.events import (
    event_cancel,
    event_publish,
    event_set_image,
    event_update,
)
from apps.users.permissions import IsOwnerOrAdmin, IsVerified


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
            400: OpenApiResponse(description='Ошибка валидации'),
            401: OpenApiResponse(description='Неверный аутентификационный токен'),
            403: OpenApiResponse(description='Требуется верифицированный пользователь')
        },
        examples=[
            OpenApiExample(
                name='Пример запроса',
                value={
                    'title': 'NEON AFTERDARK - ночь за пределами реальности',
                    'description': 'Одна ночь, три сцены и десятки артистов электронной музыки. Индустриальное пространство превратится в огромную площадку с неоновыми инсталляциями, экспериментальным светом и атмосферой андеграундной культуры. В программе: techno, melodic house, industrial и ambient. Дресс-код приветствуется, но не обязателен. Приходи за музыкой, знакомствами и впечатлениями, которые останутся надолго.',
                    'category': 1,
                    'address': 'Москва, Дизайн-завод, Большая Новодмитровская улица, 36',
                    'start_at': '2026-12-19T18:00:00Z',
                    'end_at': '2026-12-20T04:00:00Z',
                    'capacity': 850,
                    'price': '0.00'
                },
                request_only=True
            )
        ]
    )
)
class ListCreateEventView(ListCreateAPIView):
    '''
    Представление для получения списка любых опубликованных мероприятий 
    или создания мероприятия.
    '''

    queryset = EventSelector.public_events()
    filter_backends = (SearchFilter, DjangoFilterBackend)
    filterset_class = EventFilter
    search_fields = ('title', 'description', 'address')
    

    def get_authenticators(self):
        request = getattr(self, 'request', None)
        if request is not None and request.method == 'GET':
            return []
        
        return super().get_authenticators()

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]

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


@extend_schema_view(
    get=extend_schema(
        tags=['Events'],
        summary='Получить детали мероприятия',
        description='Получает детали мероприятия по его ID.',
        responses={
            200: EventOutputDetailSerializer,
            401: OpenApiResponse(description='Неверный аутентификационный токен'),
            403: OpenApiResponse(description='Требуется владелец или администратор для доступа к черновику'),
            404: OpenApiResponse(description='Мероприятия не существует')
        }
    ),
    patch=extend_schema(
        tags=['Events'],
        summary='Обновить мероприятие',
        description='Обновляет мероприятие по его ID',
        request=EventUpdateSerializer,
        responses={
            200: EventOutputDetailSerializer,
            400: OpenApiResponse(description='Ошибка валидации'),
            401: OpenApiResponse(description='Неверный аутентификационный токен'),
            403: OpenApiResponse(description='Требуется владелец или администратор'),
            404: OpenApiResponse(description='Мероприятия не существует'),
            409: OpenApiResponse(description='Мероприятие завершилось или отменилось / Попытка изменить организатора у опубликованного мероприятия')
        },
        examples=[
            OpenApiExample(
                name='Пример запроса',
                value={
                    'title': 'NEON AFTERDARK: Новая орбита',
                    'description': 'Продолжение ночного музыкального фестиваля NEON AFTERDARK. Электронная музыка, визуальные инсталляции, лазерные шоу и несколько тематических танцполов. В программе выступления приглашённых диджеев, интерактивные зоны и специальные световые перформансы.',
                    'category': 1,
                    'address': 'Москва, Берсеневская набережная, 6, стр. 3',
                    'start_at': '2026-12-19T17:00:00Z',
                    'end_at': '2026-12-19T20:00:00Z',
                    'capacity': 900,
                    'price': '0.00'
                },
                request_only=True
            )
        ]
    )
)
class RetrieveUpdateEventView(RetrieveAPIView):
    '''
    Представление извлечения или обновления мероприятия по его ID.
    '''

    serializer_class = EventOutputDetailSerializer
    lookup_url_kwarg = 'id'

    def get_queryset(self):
        return EventSelector.visible_to(viewer=self.request.user).select_related('user')

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated(), IsOwnerOrAdmin()]

    def patch(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()

        input_serializer = EventUpdateSerializer(instance, data=request.data, partial=True)
        input_serializer.is_valid(raise_exception=True)

        event = event_update(event_id=instance.pk, event_input=input_serializer.validated_data)

        output_serializer = EventOutputDetailSerializer(instance=event)

        return Response(output_serializer.data)


@extend_schema_view(
    put=extend_schema(
        tags=['Events'],
        summary='Обновить изображение мероприятия',
        description='Заменяет изображение мероприятия по его ID.',
        request=EventImageUploadSerializer,
        responses={
            200: EventOutputSerializer,
            400: OpenApiResponse(description='Ошибка валидации'),
            401: OpenApiResponse(description='Неверный аутентификационный токен'),
            403: OpenApiResponse(description='Требуется владелец или администратор'),
            404: OpenApiResponse(description='Мероприятия не существует'),
            409: OpenApiResponse(description='Мероприятие уже завершилось или отменилось / Файл не является корректным изображением / ' \
                                            'Файл имеет недопустимый формат / Файл слишком большой / Файл слишком широкий или высокий')
        }
    )
)
class UploadEventImageView(GenericAPIView):
    '''
    Представление для загрузки изображения мероприятия.
    '''

    serializer_class = EventImageUploadSerializer
    permission_classes = (IsOwnerOrAdmin,)
    parser_classes = (MultiPartParser,)
    queryset = Event.objects.all().select_related('user')
    lookup_url_kwarg = 'id'

    def put(self, request: Request, *args, **kwargs) -> Response:
        event = self.get_object()
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        event = event_set_image(event_id=event.pk, **input_serializer.validated_data)

        output_serializer = EventOutputSerializer(instance=event)
        return Response(output_serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    post=extend_schema(
        tags=['Events'],
        summary='Опубликовать мероприятие',
        description='Опубликовывает мероприятие',
        request=OpenApiRequest(),
        responses={
            200: EventOutputSerializer,
            401: OpenApiResponse(description='Неверный аутентификационный токен'),
            403: OpenApiResponse(description='Требуется владелец или администратор'),
            404: OpenApiResponse(description='Мероприятия не существует.'),
            409: OpenApiResponse(description='Не загружена картинка / Мероприятие уже началось / Уже было опубликовано')
        }
    )
)
class EventPublishView(GenericAPIView):
    '''
    Представление для перевода мероприятия в статус опубликованного.
    '''

    serializer_class = EventOutputSerializer
    permission_classes = (IsOwnerOrAdmin,)
    queryset = Event.objects.all().select_related('user')
    lookup_url_kwarg = 'id'

    def post(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()

        event = event_publish(event_id=instance.pk)

        serializer = self.get_serializer(instance=event)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    post=extend_schema(
        tags=['Events'],
        summary='Отменить мероприятие',
        description='Отменяет мероприятие',
        request=OpenApiRequest(),
        responses={
            200: EventOutputSerializer,
            401: OpenApiResponse(description='Неверный аутентификационный токен'),
            403: OpenApiResponse(description='Требуется владелец или администратор'),
            404: OpenApiResponse(description='Мероприятия не существует'),
            409: OpenApiResponse(description='Мероприятие уже завершилось / Находится в статусе черновика / Уже началось')
        }
    )
)
class EventCancelView(GenericAPIView):
    '''
    Представление для перевода мероприятия в статус отмененного.
    '''

    serializer_class = EventOutputSerializer
    permission_classes = (IsOwnerOrAdmin,)
    queryset = Event.objects.all().select_related('user')
    lookup_url_kwarg = 'id'

    def post(self, request: Request, *args, **kwargs) -> Response:
        instance = self.get_object()

        event = event_cancel(event_id=instance.pk)

        serializer = self.get_serializer(instance=event)
        return Response(serializer.data, status=status.HTTP_200_OK)