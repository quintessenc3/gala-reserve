import random
import re
from datetime import timedelta

import pytest
from apps.users.models import OneTimeCode, OneTimeCodePurpose, User
from apps.users.services.auth import otp_issue, user_register
from django.db import IntegrityError
from pytest_mock import MockerFixture

TEST_PASSWORD = 'P@ssw0rd'


@pytest.fixture
def send_verification_email_mock(mocker: MockerFixture):
    return mocker.patch('apps.users.tasks.auth.send_verification_email.delay')


@pytest.fixture
def user_payload():
    return {
        'email': 'user_1@example.com',
        'username': 'User',
        'password': 'P@ssw0rd',
        'first_name': 'John',
        'last_name': 'Doe'
    }


class TestRegister:
    def test_normal_register(self, transactional_db, send_verification_email_mock, user_payload):
        user = user_register(**user_payload)

        assert User.objects.count() == 1
        assert user.is_email_verified == False
        assert user.is_active == True
        assert user.check_password(TEST_PASSWORD)
        assert user.password != TEST_PASSWORD

        send_verification_email_mock.assert_called_once()

    def test_unique_user_username(self, db, send_verification_email_mock, user_payload):
        user_register(**user_payload)

        with pytest.raises(IntegrityError):
            user_payload['email'] = 'user_2@example.com'
            user_register(**user_payload)

    def test_unique_user_email(self, db, send_verification_email_mock, user_payload):
        user_register(**user_payload)

        with pytest.raises(IntegrityError):
            user_payload['username'] = 'User2'
            user_register(**user_payload)

    def test_failure_in_otp_issue_leaves_no_user(self, db, mocker, send_verification_email_mock, user_payload):
        mocker.patch('apps.users.services.auth.otp_issue', side_effect=RuntimeError)

        with pytest.raises(RuntimeError):
            user_register(**user_payload)

        assert not User.objects.exists()                         


class TestOTPIssue:
    def test_normal_issue(self, user: User):
        otp, code = otp_issue(user.pk, OneTimeCodePurpose.EMAIL_VERIFICATION)

        assert OneTimeCode.objects.count() == 1
        assert otp.user == user
        assert otp.purpose == OneTimeCodePurpose.EMAIL_VERIFICATION
        assert otp.code_hash != code
        assert otp.is_expired == False
        assert otp.is_reached_attempts_limit == False
        assert len(code) == OneTimeCode.CODE_LENGTH
        assert re.match(f'[0-9]{{{OneTimeCode.CODE_LENGTH}}}', code)

    @pytest.mark.parametrize(('field', 'value'), [
        ('created_at', OneTimeCode.TTL_MINUTES),
        ('attempts', OneTimeCode.MAX_ATTEMPTS)
    ])
    def test_update_otp_code_if_expired_or_attempts_limit(self, field: str, value: timedelta | int, user: User):
        old_otp, old_code = otp_issue(user.pk, OneTimeCodePurpose.EMAIL_VERIFICATION)
        setattr(
            old_otp,
            field,
            getattr(old_otp, field) + value
        )
        old_otp.save()

        otp, code = otp_issue(user.pk, OneTimeCodePurpose.EMAIL_VERIFICATION)
        
        assert old_otp.pk == otp.pk
        assert old_otp.code_hash != otp.code_hash
        assert old_code != code
        assert otp.is_expired == False
        assert otp.attempts == 0