from datetime import timedelta

from apps.events.factories import EventFactory
from apps.events.models import EventStatus
from apps.events.tasks.events import complete_finished_events
from django.utils import timezone


class TestCompleteFinishedEvents:
    def test_completes_only_finished_published_events(self, db):
        now = timezone.now()
        finished_event = EventFactory.create(
            status=EventStatus.PUBLISHED,
            start_at=now - timedelta(days=2),
            end_at=now - timedelta(days=1),
        )
        previous_updated_at = finished_event.updated_at
        upcoming_event = EventFactory.create(
            status=EventStatus.PUBLISHED,
            start_at=now - timedelta(hours=1),
            end_at=now + timedelta(hours=1),
        )
        draft_event = EventFactory.create(
            status=EventStatus.DRAFT,
            start_at=now - timedelta(days=2),
            end_at=now - timedelta(days=1),
        )
        cancelled_event = EventFactory.create(
            status=EventStatus.CANCELLED,
            start_at=now - timedelta(days=2),
            end_at=now - timedelta(days=1),
        )

        complete_finished_events()

        finished_event.refresh_from_db()
        upcoming_event.refresh_from_db()
        draft_event.refresh_from_db()
        cancelled_event.refresh_from_db()

        assert finished_event.status == EventStatus.COMPLETED
        assert finished_event.updated_at > previous_updated_at
        assert upcoming_event.status == EventStatus.PUBLISHED
        assert draft_event.status == EventStatus.DRAFT
        assert cancelled_event.status == EventStatus.CANCELLED
