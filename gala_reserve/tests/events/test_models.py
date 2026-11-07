from datetime import timedelta
from decimal import Decimal

import pytest
from apps.events.factories import CategoryFactory, EventFactory
from apps.events.models import EventStatus
from django.db import IntegrityError
from django.utils import timezone


class TestCategory:
    def test_normal_category(self, db):
        CategoryFactory.create()

    def test_unique_category_name_constraint(self, db):
        CategoryFactory.create(name='Категория')

        with pytest.raises(IntegrityError):
            CategoryFactory.create(name='категория')

class TestEvent:
    def test_normal_event(self, db):
        EventFactory.create()

    def test_capacity_gte_seats_taken_constraint(self, db):
        with pytest.raises(IntegrityError):
            EventFactory.create(capacity=1, seats_taken=2)

    def test_price_gte_0_constraint(self, db):
        with pytest.raises(IntegrityError):
            EventFactory.create(price=Decimal('-1.00'))

    @pytest.mark.parametrize('value', (0, 100_001))
    def test_capacity_gte_1_lte_100000_constraint(self, db, value):
        with pytest.raises(IntegrityError):
            EventFactory.create(capacity=value)

    @pytest.mark.parametrize('add_second_amt', (0, 1))
    def test_end_at_gt_start_at_constraint(self, db, add_second_amt):
        start_at = timezone.now()

        with pytest.raises(IntegrityError):
            EventFactory.create(start_at=start_at + timedelta(seconds=add_second_amt), end_at=start_at)

    def test_status_in_allowed_statuses_constraint(self, db):
        with pytest.raises(IntegrityError):
            EventFactory.create(status='unexisting_status')

    @pytest.mark.parametrize(('status', 'published_at'), [
        (EventStatus.DRAFT, timezone.now()),
        (EventStatus.PUBLISHED, None)
    ])
    def test_published_at_matches_status_constraint(self, db, status, published_at):
        with pytest.raises(IntegrityError):
            EventFactory.create(status=status, published_at=published_at)