from apps.events.factories import CategoryFactory, EventFactory
from apps.events.models import Category, EventStatus
from apps.events.serializers.categories import (
    CategoryInputSerializer,
    CategoryOutputSerializer,
)
from django.db.models import Count, Q


class TestCategoryOutputSerializer:
    def test_events_count_field(self, db):
        category = CategoryFactory.create()
        other_category = CategoryFactory.create()

        for _ in range(3):
            EventFactory.create(category=category, status=EventStatus.PUBLISHED)
        EventFactory.create(category=category, status=EventStatus.DRAFT)
        for _ in range(2):
            EventFactory.create(category=other_category, status=EventStatus.PUBLISHED)

        category = Category.objects.annotate(
            events_count=Count('events', filter=~Q(events__status=EventStatus.DRAFT))
        ).get(pk=category.pk)
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