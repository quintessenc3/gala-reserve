import pytest
from apps.users.factories import UserFactory
from apps.users.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError


def test_normal_user_full_clean(db):
    user = UserFactory.build(username='Aa0_Aa0')
    user.full_clean()


def test_normal_user_save(db):
    UserFactory.create()


@pytest.mark.parametrize('username', [
    'a' * (User.MIN_USERNAME_LENGTH - 1),
    'a' * (User.MAX_USERNAME_LENGTH + 1),
    '@#$%^&*()-+~`'
])
def test_username_regex(username: str):
    user = UserFactory.build(username=test_username_regex)
    with pytest.raises(ValidationError):
        user.clean_fields(exclude={'password'})


def test_unique_email_constraint(db):
    UserFactory.create(email='user@example.com')
    with pytest.raises(IntegrityError):
        UserFactory.create(email='USER@example.com')


def test_unique_username_constraint(db):
    UserFactory.create(username='testuser')
    with pytest.raises(IntegrityError):
        UserFactory.create(username='TESTUSER')