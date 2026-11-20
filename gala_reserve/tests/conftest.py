from types import SimpleNamespace

import pytest
from apps.users.factories import UserFactory
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture
def user(db):
    return UserFactory.create()

@pytest.fixture
def other_user(db):
    return UserFactory.create()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def auth_client(user, api_client) -> APIClient:
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def verified_client(user, api_client) -> APIClient:
    user.is_email_verified = True
    user.save(update_fields=['is_email_verified'])
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def serializer_context(user):
    return {'request': SimpleNamespace(user=user)}


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    cache.clear()