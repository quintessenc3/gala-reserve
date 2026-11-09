import pytest
from apps.events.factories import CategoryFactory, EventFactory
from apps.events.services.categories import CategoryInUseError, category_delete


class TestCategoryDelete:
    @pytest.fixture(autouse=True)
    def setup(self, user):
        self.category = CategoryFactory.create(user=user)

    def test_normal_delete(self):
        category_delete(category_id=self.category.pk)

    def test_delete_if_events_in_category_exists(self, user):
        EventFactory.create(category=self.category, user=user)

        with pytest.raises(CategoryInUseError):
            category_delete(category_id=self.category.pk)