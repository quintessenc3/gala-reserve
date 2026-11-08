from apps.events.factories import CategoryFactory, EventFactory
from apps.events.serializers.categories import (
    CategoryCreateSerializer,
    CategoryOutputSerializer,
)


class TestCategoryOutputSerializer:
    def test_events_count_field(self, db):
        category = CategoryFactory.create()

        for _ in range(3):
            EventFactory.create(category=category)

        serializer = CategoryOutputSerializer(instance=category)
        assert serializer.data['events_count'] == 3


class TestCategoryCreateSerializer:
    def test_unique_name_lookup(self, user):
        CategoryFactory.create(name='Birthdays')
        serializer = CategoryCreateSerializer(data={
            'name': 'birthdays',
            'description': 'description',
            'created_by': user.pk
        })

        assert serializer.is_valid() == False
        assert 'name' in serializer.errors