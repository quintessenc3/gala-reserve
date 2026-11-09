from apps.events.factories import EventFactory
from apps.events.models import EventStatus
from apps.events.selectors import EventSelector


class TestEventSelector:
    def test_public_events_returns_only_published_event(self, db):
        published_event = EventFactory.create(status=EventStatus.PUBLISHED)
        EventFactory.create(status=EventStatus.DRAFT)

        assert list(EventSelector.public_events()) == [published_event]
