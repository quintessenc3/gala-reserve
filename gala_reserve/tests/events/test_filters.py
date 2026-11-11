from datetime import timedelta
from decimal import Decimal

import pytest
from apps.events.factories import CategoryFactory, EventFactory
from apps.events.filters import EventFilter
from apps.events.models import Event, EventStatus
from django.utils import timezone
from rest_framework.exceptions import ValidationError


class TestEventFilter:
    def filtered_event_ids(data):
        return list(
            EventFilter(data=data, queryset=Event.objects.all()).qs.values_list('pk', flat=True)
        )

    def test_price_min_is_inclusive(self, db):
        cheaper = EventFactory.create(price=Decimal('9.99'))
        boundary = EventFactory.create(price=Decimal('10.00'))
        more_expensive = EventFactory.create(price=Decimal('10.01'))

        assert set(self.filtered_event_ids({'price_min': '10.00'})) == {
            boundary.pk,
            more_expensive.pk,
        }
        assert cheaper.pk not in self.filtered_event_ids({'price_min': '10.00'})

    def test_price_max_is_inclusive(self, db):
        cheaper = EventFactory.create(price=Decimal('9.99'))
        boundary = EventFactory.create(price=Decimal('10.00'))
        more_expensive = EventFactory.create(price=Decimal('10.01'))

        assert set(self.filtered_event_ids({'price_max': '10.00'})) == {
            cheaper.pk,
            boundary.pk,
        }
        assert more_expensive.pk not in self.filtered_event_ids({'price_max': '10.00'})

    def test_price_min_greater_than_price_max_raises_validation_error(self, db):
        with pytest.raises(ValidationError) as exc_info:
            self.filtered_event_ids({'price_min': '10.01', 'price_max': '10.00'})

        assert 'price_min' in exc_info.value.detail

    def test_equal_price_min_and_price_max_is_valid(self, db):
        boundary = EventFactory.create(price=Decimal('10.00'))
        EventFactory.create(price=Decimal('9.99'))
        EventFactory.create(price=Decimal('10.01'))

        assert self.filtered_event_ids({'price_min': '10.00', 'price_max': '10.00'}) == [boundary.pk]

    def test_start_from_is_inclusive(self, db):
        now = timezone.now()
        earlier = EventFactory.create(start_at=now - timedelta(days=1))
        boundary = EventFactory.create(start_at=now)
        later = EventFactory.create(start_at=now + timedelta(days=1))

        result_ids = self.filtered_event_ids({'start_from': now.isoformat()})

        assert set(result_ids) == {boundary.pk, later.pk}
        assert earlier.pk not in result_ids

    def test_start_to_is_inclusive(self, db):
        now = timezone.now()
        earlier = EventFactory.create(start_at=now - timedelta(days=1))
        boundary = EventFactory.create(start_at=now)
        later = EventFactory.create(start_at=now + timedelta(days=1))

        result_ids = self.filtered_event_ids({'start_to': now.isoformat()})

        assert set(result_ids) == {earlier.pk, boundary.pk}
        assert later.pk not in result_ids

    def test_start_from_greater_than_start_to_raises_validation_error(self, db):
        now = timezone.now()
        start_from = now + timedelta(days=1)
        start_to = now

        with pytest.raises(ValidationError) as exc_info:
            self.filtered_event_ids({
                'start_from': start_from.isoformat(),
                'start_to': start_to.isoformat(),
            })

        assert 'start_from' in exc_info.value.detail

    def test_equal_start_from_and_start_to_is_valid(self, db):
        boundary = timezone.now()
        event = EventFactory.create(start_at=boundary)
        EventFactory.create(start_at=boundary - timedelta(seconds=1))
        EventFactory.create(start_at=boundary + timedelta(seconds=1))

        assert self.filtered_event_ids({
            'start_from': boundary.isoformat(),
            'start_to': boundary.isoformat(),
        }) == [event.pk]

    @pytest.mark.parametrize('status', (EventStatus.PUBLISHED, EventStatus.COMPLETED, EventStatus.CANCELLED))
    def test_status_filters_each_public_status(self, db, status):
        event = EventFactory.create(status=status)
        EventFactory.create(
            status=next(candidate for candidate in EventStatus.values if candidate != status)
        )

        assert self.filtered_event_ids({'status': status}) == [event.pk]

    def test_status_does_not_allow_draft(self, db):
        EventFactory.create(status=EventStatus.DRAFT)
        EventFactory.create(status=EventStatus.PUBLISHED)
        event_filter = EventFilter(data={'status': EventStatus.DRAFT}, queryset=Event.objects.all())

        assert not event_filter.form.is_valid()

    def test_category_filters_events(self, db):
        category = CategoryFactory.create()
        matching = EventFactory.create(category=category)
        EventFactory.create()

        assert self.filtered_event_ids({'category': str(category.pk)}) == [matching.pk]

    def test_user_filters_events(self, user, other_user, db):
        matching = EventFactory.create(user=user)
        EventFactory.create(user=other_user)

        assert self.filtered_event_ids({'user': str(user.pk)}) == [matching.pk]

    @pytest.mark.parametrize(
        ('ordering', 'expected_order'),
        (
            ('start_at', ('earliest', 'middle', 'latest')),
            ('-start_at', ('latest', 'middle', 'earliest')),
            ('price', ('earliest', 'middle', 'latest')),
            ('-price', ('latest', 'middle', 'earliest')),
            ('created_at', ('earliest', 'middle', 'latest')),
            ('-created_at', ('latest', 'middle', 'earliest')),
            ('popularity', ('earliest', 'middle', 'latest')),
            ('-popularity', ('latest', 'middle', 'earliest')),
        ),
    )
    def test_ordering_filter(self, db, ordering, expected_order):
        now = timezone.now()
        events = {
            'earliest': EventFactory.create(
                start_at=now + timedelta(days=1),
                price=Decimal('10.00'),
                seats_taken=1,
            ),
            'middle': EventFactory.create(
                start_at=now + timedelta(days=2),
                price=Decimal('20.00'),
                seats_taken=2,
            ),
            'latest': EventFactory.create(
                start_at=now + timedelta(days=3),
                price=Decimal('30.00'),
                seats_taken=3,
            ),
        }
        Event.objects.filter(pk=events['earliest'].pk).update(created_at=now + timedelta(days=1))
        Event.objects.filter(pk=events['middle'].pk).update(created_at=now + timedelta(days=2))
        Event.objects.filter(pk=events['latest'].pk).update(created_at=now + timedelta(days=3))

        result_ids = self.filtered_event_ids({'ordering': ordering})

        assert result_ids == [events[name].pk for name in expected_order]
