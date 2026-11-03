import pytest
from apps.users.factories import UserFactory


@pytest.fixture
def user(db):
    return UserFactory.create()