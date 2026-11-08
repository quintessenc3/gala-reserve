from rest_framework import serializers

from apps.events.models import Category


class CategoryOutputSerializer(serializers.ModelSerializer):
    '''
    Сериализатор выходных данных категории.
    '''

    events_count = serializers.IntegerField(source='events.count')

    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'events_count')