import pytest
from apps.users.factories import UserFactory
from rest_framework.test import APIClient


@pytest.fixture
def user(db):
    return UserFactory.create()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def auth_client(user, api_client) -> APIClient:
    api_client.force_authenticate(user=user)
    return api_client