from rest_framework import serializers

from apps.events.models import Event


class EventOutputSerializer(serializers.ModelSerializer):
    '''
    Сериализатор выходных данных мероприятия.
    '''
    
    class Meta:
        model = Event
        fields = ('title', 'description', 'category', 'user', 'image', 'address',
                  'start_at', 'end_at', 'capacity', 'seats_taken', 'price', 'status',
                  'created_at', 'updated_at', 'published_at')