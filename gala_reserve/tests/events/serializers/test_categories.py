from apps.events.factories import CategoryFactory, EventFactory
from apps.events.serializers.categories import CategoryOutputSerializer


class TestCategoryOutputSerializer:
    def test_events_count_field(self, db):
        category = CategoryFactory.create()

        for _ in range(3):
            EventFactory.create(category=category)

        serializer = CategoryOutputSerializer(instance=category)
        assert serializer.data['events_count'] == 3