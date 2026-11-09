from rest_framework import serializers

from apps.core.serializer_validators import FieldGreaterThanOtherValidator
from apps.events.models import Event


class EventOutputSerializer(serializers.ModelSerializer):
    '''
    Сериализатор выходных данных мероприятия.
    '''
    
    class Meta:
        model = Event
        fields = ('id', 'title', 'description', 'category', 'user', 'image', 'address',
                  'start_at', 'end_at', 'capacity', 'seats_taken', 'price', 'status',
                  'created_at', 'updated_at', 'published_at')


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