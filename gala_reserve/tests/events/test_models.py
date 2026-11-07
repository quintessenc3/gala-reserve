import pytest
from apps.events.factories import CategoryFactory
from django.db import IntegrityError


class TestCategory:
    def test_normal_category(self, db):
        CategoryFactory.create()

    def test_unique_category_name_constraint(self, db):
        CategoryFactory.create(name='Категория')

        with pytest.raises(IntegrityError):
            CategoryFactory.create(name='категория')