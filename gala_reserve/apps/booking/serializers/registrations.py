from rest_framework import serializers

from apps.booking.models import Registration
from apps.events.models import Event


class RegistrationEventOutputSerializer(serializers.ModelSerializer):
    '''
    Сериализатор выходных данных мероприятия в регистрации.
    '''

    class Meta:
        model = Event
        fields = ('id', 'title', 'image', 'start_at', 'end_at')


class RegistrationOutputSerializer(serializers.ModelSerializer):
    '''
    Сериализатор выходных данных регистрации.
    '''

    event = RegistrationEventOutputSerializer()

    class Meta:
        model = Registration
        fields = ('id', 'user', 'event', 'status', 'cancel_reason', 'confirmed_at', 'cancelled_at')