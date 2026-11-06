import random
import re
from datetime import timedelta

import freezegun
import pytest
from apps.users.models import OneTimeCode, OneTimeCodePurpose, User
from apps.users.services.auth import (
    AlreadyVerified,
    CodeExpiredError,
    InvalidCodeError,
    TooManyAttempts,
    otp_issue,
    user_email_verify,
    user_register,
    otp_resend
)
from django.db import IntegrityError
from django.utils import timezone
from pytest_mock import MockerFixture
from rest_framework import exceptions

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


@pytest.fixture
def user_otp_code(user: User) -> tuple[OneTimeCode, str | None]:
    return otp_issue(user.pk, OneTimeCodePurpose.EMAIL_VERIFICATION)


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
        ('created_at', -OneTimeCode.TTL_MINUTES),
        ('attempts', OneTimeCode.MAX_ATTEMPTS)
    ])
    def test_update_otp_code_if_expired_or_attempts_limit(self, field: str, value: timedelta | int, user: User):
        old_otp, old_code = otp_issue(user.pk, OneTimeCodePurpose.EMAIL_VERIFICATION)
        setattr(old_otp, field, getattr(old_otp, field) + value)
        old_otp.save()

        otp, code = otp_issue(user.pk, OneTimeCodePurpose.EMAIL_VERIFICATION)
        
        assert old_otp.pk == otp.pk
        assert old_otp.code_hash != otp.code_hash
        assert old_code != code
        assert otp.is_expired == False
        assert otp.attempts == 0


class TestUserEmailVerify:
    def test_normal_email_verify(self, user, user_otp_code):
        with freezegun.freeze_time('2016-09-10 12:00:00'):
            otp, code = user_otp_code
            user_email_verify(user_id=user.pk, code=code)

            otp.refresh_from_db()
            user.refresh_from_db()

            assert otp.used_at is not None
            assert otp.used_at == timezone.now()
            assert user.is_email_verified == True

    def test_user_does_not_exist(self, user, user_otp_code):
        _, code = user_otp_code
        with pytest.raises(exceptions.NotFound):
            user_email_verify(user_id=1, code=code)

    def test_user_already_verified(self, user, user_otp_code):
        _, code = user_otp_code
        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])

        with pytest.raises(AlreadyVerified):
            user_email_verify(user_id=user.pk, code=code)

    def test_code_does_not_exist(self, user):
        with pytest.raises(InvalidCodeError):
            user_email_verify(user_id=user.pk, code='000000')

    def test_code_with_right_purpose_does_not_exist(self, user, user_otp_code):
        otp, code = user_otp_code
        otp.purpose = OneTimeCodePurpose.PASSWORD_RESET
        otp.save(update_fields=['purpose'])

        with pytest.raises(InvalidCodeError):
            user_email_verify(user_id=user.pk, code=code)

    def test_invalid_code(self, user, user_otp_code):
        otp, _ = user_otp_code
        with pytest.raises(InvalidCodeError):
            user_email_verify(user_id=user.pk, code='000000')
        otp.refresh_from_db()
        assert otp.attempts == 1

    def test_too_many_attempts(self, user, user_otp_code):
        otp, _ = user_otp_code

        for _ in range(OneTimeCode.MAX_ATTEMPTS - 1):
            with pytest.raises(InvalidCodeError):
                user_email_verify(user_id=user.pk, code='000000')

        otp.refresh_from_db()
        assert otp.attempts == OneTimeCode.MAX_ATTEMPTS - 1

        with pytest.raises(TooManyAttempts):
            user_email_verify(user_id=user.pk, code='000000')

        otp.refresh_from_db()
        assert otp.attempts == OneTimeCode.MAX_ATTEMPTS

    def test_code_has_expired(self, user, user_otp_code):
        otp, code = user_otp_code
        with (
            freezegun.freeze_time(otp.created_at + OneTimeCode.TTL_MINUTES), 
            pytest.raises(CodeExpiredError)
        ):
            user_email_verify(user_id=user.pk, code=code)

    def test_atomicity(self, mocker: MockerFixture, user, user_otp_code):
        otp, code = user_otp_code

        original_save = User.save

        def save_then_fail(self, *args, **kwargs):
            original_save(self, *args, **kwargs)
            raise RuntimeError

        save_mock = mocker.patch.object(
            User, 'save', autospec=True, side_effect=save_then_fail
        )

        with pytest.raises(RuntimeError):
            user_email_verify(user_id=user.pk, code=code)

        save_mock.assert_called_once()

        otp.refresh_from_db()
        user.refresh_from_db()

        assert otp.used_at is None
        assert otp.attempts == 0
        assert not user.is_email_verified


class TestOtpResend:
    def test_normal_resend(self, user, send_verification_email_mock):
        otp_resend(user_id=user.pk)
        send_verification_email_mock.assert_called_once()

    def test_unexisting_user_does_not_exist(self, db, send_verification_email_mock):
        with pytest.raises(exceptions.NotFound):
            otp_resend(user_id=-1)

        send_verification_email_mock.assert_not_called()

    def test_user_already_verified(self, user, send_verification_email_mock):
        user.is_email_verified = True
        user.save()

        with pytest.raises(AlreadyVerified):
            otp_resend(user_id=user.pk)

        send_verification_email_mock.assert_not_called()