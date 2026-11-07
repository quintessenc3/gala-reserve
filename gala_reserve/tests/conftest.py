import pytest
from apps.users.factories import UserFactory
from pytest_mock import MockerFixture
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
def send_verification_email_mock(mocker: MockerFixture):
    return mocker.patch('apps.users.tasks.auth.send_verification_email.delay')


@pytest.fixture
def send_password_reset_email_mock(mocker: MockerFixture):
    return mocker.patch('apps.users.tasks.auth.send_password_reset_email.delay')