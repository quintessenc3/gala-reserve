from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.events.models import Category


class CategoryOutputSerializer(serializers.ModelSerializer):
    '''
    Сериализатор выходных данных категории.
    '''

    events_count = serializers.IntegerField(source='events.count')

    class Meta:
        model = Category
        fields = ('id', 'name', 'description', 'events_count')


class CategoryInputSerializer(serializers.ModelSerializer):
    '''
    Сериализатор входных данных для создания категории.
    '''

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Category
        fields = ('name', 'description', 'user')
        extra_kwargs = {
            'name': {
                'validators': [
                    UniqueValidator(
                        queryset=(Category.objects.all()),
                        lookup='iexact'
                    )
                ]
            }
        }