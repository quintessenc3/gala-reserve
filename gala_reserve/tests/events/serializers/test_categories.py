from apps.events.factories import CategoryFactory, EventFactory
from apps.events.serializers.categories import (
    CategoryInputSerializer,
    CategoryOutputSerializer,
)


class TestCategoryOutputSerializer:
    def test_events_count_field(self, db):
        category = CategoryFactory.create()

        for _ in range(3):
            EventFactory.create(category=category)

        serializer = CategoryOutputSerializer(instance=category)
        assert serializer.data['events_count'] == 3


class TestCategoryInputSerializer:
    def test_unique_name_lookup(self, serializer_context):
        CategoryFactory.create(name='Birthdays')
        serializer = CategoryInputSerializer(data={
            'name': 'birthdays',
            'description': 'description'
        }, context=serializer_context)

        assert serializer.is_valid() == False
        assert 'name' in serializer.errors