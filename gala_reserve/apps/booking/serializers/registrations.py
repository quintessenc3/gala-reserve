from rest_framework import serializers

from apps.booking.models import Registration, Ticket
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


class TicketEventOutputSerializer(serializers.ModelSerializer):
    '''
    Сериализатор выходных данных мероприятия в билете.
    '''

    class Meta:
        model = Event
        fields = ('id', 'title', 'image', 'address', 'start_at', 'end_at', 'status')


class TicketOutputSerializer(serializers.ModelSerializer):
    '''
    Сериализатор выходных данных билета.
    '''

    event = TicketEventOutputSerializer()

    class Meta:
        model = Ticket
        fields = ('id', 'event', 'status', 'created_at', 'used_at')