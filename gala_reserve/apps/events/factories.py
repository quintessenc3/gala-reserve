import factory

from apps.events.models import Category
from apps.users.factories import UserFactory


class CategoryFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f'Category {n}')
    description = factory.Faker('paragraph')
    created_by = factory.SubFactory(UserFactory)

    class Meta:
        model = Category