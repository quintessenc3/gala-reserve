from django.contrib.auth.models import AnonymousUser

from apps.events.factories import EventFactory
from apps.events.models import EventStatus
from apps.events.selectors import EventSelector


class TestEventSelector:
    def test_public_events_returns_only_published_event(self, db):
        published_event = EventFactory.create(status=EventStatus.PUBLISHED)
        EventFactory.create(status=EventStatus.DRAFT)

        assert list(EventSelector.public_events()) == [published_event]

    def test_staff_user_can_see_events_with_any_status(self, user):
        user.is_staff = True
        events = [
            EventFactory.create(user=user, status=status)
            for status in EventStatus.values
        ]

        visible_events = EventSelector.visible_to(viewer=user)

        assert set(visible_events) == set(events)

    def test_unauthenticated_user_can_only_see_non_draft_events(self, db):
        events_by_status = {
            status: EventFactory.create(status=status)
            for status in EventStatus.values
        }

        visible_events = EventSelector.visible_to(viewer=AnonymousUser())

        assert set(visible_events) == {
            event
            for status, event in events_by_status.items()
            if status != EventStatus.DRAFT
        }

    def test_my_events_returns_only_my_any_events(self, user, other_user):
        my_events = [
            EventFactory.create(user=user, status=status)
            for status in EventStatus.values
        ]
        for status in EventStatus.values:
            EventFactory.create(user=other_user, status=status)

        assert set(EventSelector.my_events(viewer=user)) == set(my_events)

    def test_authenticated_user_can_see_only_their_own_draft_events(self, user, other_user):
        own_draft = EventFactory.create(user=user, status=EventStatus.DRAFT)
        EventFactory.create(user=other_user, status=EventStatus.DRAFT)
        non_draft_events = [
            EventFactory.create(user=other_user, status=status)
            for status in EventStatus.values
            if status != EventStatus.DRAFT
        ]

        visible_events = EventSelector.visible_to(viewer=user)

        assert set(visible_events) == {own_draft, *non_draft_events}
