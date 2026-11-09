from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone

from apps.events.models import Category, Event, EventStatus
from apps.users.factories import UserFactory


class CategoryFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'Category {n}')
    description = factory.Faker('paragraph')
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = Category


class EventFactory(factory.django.DjangoModelFactory):
    title = factory.Sequence(lambda n: f'Event {n}')
    description = factory.Faker('paragraph', nb_sentences=5)
    category = factory.SubFactory(CategoryFactory)
    user = factory.SubFactory(UserFactory)
    address = factory.Faker('street_address')
    start_at = factory.LazyFunction(
        lambda: timezone.now() + timedelta(days=7)
    )
    end_at = factory.LazyAttribute(
        lambda obj: obj.start_at + timedelta(days=1)
    )
    capacity = 100
    price = Decimal('0.00')
    status = EventStatus.DRAFT
    published_at = factory.LazyAttribute(lambda obj: (
            timezone.now()
            if obj.status != EventStatus.DRAFT
            else None
        )
    )

    class Meta:
        model = Event