from rest_framework import serializers

from apps.core.serializer_validators import (
    FieldGreaterThanOrEqualOtherValidator,
    FieldGreaterThanOtherValidator,
)
from apps.events.models import Category, Event
from apps.users.models import User


class EventCategoryOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name')


class EventOrganizerOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'photo')


class EventOutputSerializer(serializers.ModelSerializer):
    '''
    Сериализатор выходных данных мероприятия.
    '''

    organizer = EventOrganizerOutputSerializer(source='user')
    seats_available = serializers.SerializerMethodField()

    def get_seats_available(self, event: Event) -> int:
        return event.capacity - event.seats_taken

    class Meta:
        model = Event
        fields = ('id', 'title', 'category', 'organizer', 'image', 'address', 'start_at',
                  'end_at', 'price', 'status', 'seats_available')


class EventOutputDetailSerializer(serializers.ModelSerializer):
    '''
    Сериализатор детальных выходных данных мероприятия.
    '''

    organizer = EventOrganizerOutputSerializer(source='user')
    seats_available = serializers.SerializerMethodField()

    def get_seats_available(self, event: Event) -> int:
        return event.capacity - event.seats_taken

    class Meta:
        model = Event
        fields = ('id', 'title', 'category', 'organizer', 'image', 'address', 'start_at',
                  'end_at', 'price', 'status', 'seats_available', 'description',
                  'capacity', 'created_at')



class EventCreateSerializer(serializers.ModelSerializer):
    '''
    Сериализатор входных данных для создания мероприятия.
    '''

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Event
        fields = ('title', 'description', 'category', 'address', 'start_at', 'end_at',
                  'capacity', 'price', 'user')
        validators = (
            FieldGreaterThanOtherValidator(
                'end_at',
                'start_at',
                'Дата и время окончания не может быть раньше или равно дате и времени начала мероприятия.'
            ),
        )


class EventUpdateSerializer(serializers.ModelSerializer):
    '''
    Сериализатор входных данных для обновления мероприятия.
    '''

    seats_taken = serializers.IntegerField(read_only=True)

    class Meta:
        model = Event
        fields = ('title', 'description', 'category', 'user', 'address', 'start_at', 'end_at',
                  'capacity', 'price', 'seats_taken')
        validators = (
            FieldGreaterThanOtherValidator(
                'end_at',
                'start_at',
                'Дата и время окончания не может быть раньше или равно дате и времени начала мероприятия.'
            ),
            FieldGreaterThanOrEqualOtherValidator(
                'capacity',
                'seats_taken',
                'Вместимость мероприятия должна быть больше или равна кол-ву активных регистраций.'
            )
        )


class EventImageUploadSerializer(serializers.ModelSerializer):
    '''
    Сериализатор входных данных для обновления изображения мероприятия.
    '''

    class Meta:
        model = Event
        fields = ('image',)
        extra_kwargs = {
            'image': {'required': True}
        }