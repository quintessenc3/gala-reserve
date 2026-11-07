import re
from datetime import timedelta

import freezegun
import pytest
from apps.users.models import OneTimeCode, OneTimeCodePurpose, User
from apps.users.services.auth import (
    AlreadyVerified,
    CodeExpiredError,
    InvalidCodeError,
    PasswordsDoNotMatch,
    TooManyAttempts,
    _revoke_all_refresh_tokens,
    otp_issue,
    otp_resend,
    user_email_verify,
    user_register,
    user_request_password_reset_code,
    user_reset_password_by_code,
    user_reset_password_by_old_password,
)
from django.db import IntegrityError
from django.utils import timezone
from pytest_mock import MockerFixture
from rest_framework import exceptions
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

TEST_PASSWORD = 'P@ssw0rd'


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


class TestUserRequestPasswordResetCode:
    def test_normal_request(self, transactional_db, user, send_password_reset_email_mock):
        user_request_password_reset_code(email=user.email)
        assert OneTimeCode.objects.filter(user=user, purpose=OneTimeCodePurpose.PASSWORD_RESET).exists()
        send_password_reset_email_mock.assert_called_once()

    def test_unexisting_user_does_not_exist(self, db, send_password_reset_email_mock):
        user_request_password_reset_code(email='nonexistent@example.com')

        assert OneTimeCode.objects.count() == 0

        send_password_reset_email_mock.assert_not_called()


class TestUserResetPasswordByCode:
    new_password = 'HardP@ssw0rd'
    
    @pytest.fixture(autouse=True)
    def setup(self, user, other_user):
        self.otp, self.code = user_request_password_reset_code(email=user.email)
        self.user_tokens = [RefreshToken.for_user(user) for _ in range(2)]
        self.user_jtis = {str(t['jti']) for t in self.user_tokens}
        RefreshToken.for_user(other_user)

    @staticmethod
    def blacklisted_jtis() -> set[str]:
        return set(BlacklistedToken.objects.values_list('token__jti', flat=True))

    def assert_tokens_revoked(self):
        assert self.blacklisted_jtis() == self.user_jtis

    def assert_tokens_not_revoked(self):
        assert self.blacklisted_jtis() == set()

    def test_normal_reset(self, user):
        assert BlacklistedToken.objects.count() == 0
        assert not user.check_password(self.new_password)

        user_reset_password_by_code(email=user.email, code=self.code, password=self.new_password)

        user.refresh_from_db()
        assert user.check_password(self.new_password)
        self.otp.refresh_from_db()
        assert self.otp.used_at is not None

        self.assert_tokens_revoked()
        for token in self.user_tokens:
            with pytest.raises(TokenError):
                RefreshToken(str(token))

    def test_user_does_not_exist(self, user):
        with pytest.raises(InvalidCodeError):
            user_reset_password_by_code(
                email='nonexistent@example.com', 
                code=self.code, 
                password=self.new_password
            )

        user.refresh_from_db()
        assert not user.check_password(self.new_password)
        self.otp.refresh_from_db()
        assert self.otp.used_at is None

    def test_code_does_not_exist(self, user):
        self.otp.delete()
        with pytest.raises(InvalidCodeError):
            user_reset_password_by_code(
                email=user.email, 
                code=self.code, 
                password=self.new_password
            )

        user.refresh_from_db()
        assert not user.check_password(self.new_password)
        self.assert_tokens_not_revoked()

    def test_invalid_code(self, user):
        with pytest.raises(InvalidCodeError):
            user_reset_password_by_code(email=user.email, code='000000', password=self.new_password)

        self.otp.refresh_from_db()
        assert self.otp.attempts == 1

        user.refresh_from_db()
        assert not user.check_password(self.new_password)
        self.otp.refresh_from_db()
        assert self.otp.used_at is None
        self.assert_tokens_not_revoked()

    def test_too_many_attempts(self, user):
        for _ in range(OneTimeCode.MAX_ATTEMPTS - 1):
            with pytest.raises(InvalidCodeError):
                user_reset_password_by_code(email=user.email, code='000000', password=self.new_password)

        self.otp.refresh_from_db()
        assert self.otp.attempts == OneTimeCode.MAX_ATTEMPTS - 1

        with pytest.raises(TooManyAttempts):
            user_reset_password_by_code(email=user.email, code='000000', password=self.new_password)

        self.otp.refresh_from_db()
        assert self.otp.attempts == OneTimeCode.MAX_ATTEMPTS
        assert self.otp.used_at is None

        user.refresh_from_db()
        assert not user.check_password(self.new_password)
        self.assert_tokens_not_revoked()
        
    def test_code_has_expired(self, user):
        with (
            freezegun.freeze_time(self.otp.created_at + OneTimeCode.TTL_MINUTES), 
            pytest.raises(CodeExpiredError)
        ):
            user_reset_password_by_code(email=user.email, code=self.code, password=self.new_password)

        user.refresh_from_db()
        assert not user.check_password(self.new_password)
        self.otp.refresh_from_db()
        assert self.otp.used_at is None
        self.assert_tokens_not_revoked()

    def test_atomicity(self, mocker: MockerFixture, user):
        original_revoke = _revoke_all_refresh_tokens

        def revoke_then_fail(*args, **kwargs):
            original_revoke(*args, **kwargs)
            raise RuntimeError

        mocker.patch(
            'apps.users.services.auth._revoke_all_refresh_tokens',
            side_effect=revoke_then_fail,
        )

        with pytest.raises(RuntimeError):
            user_reset_password_by_code(email=user.email, code=self.code, password=self.new_password)

        self.otp.refresh_from_db()
        user.refresh_from_db()

        assert self.otp.used_at is None
        assert self.otp.attempts == 0
        assert not user.check_password(self.new_password)
        self.assert_tokens_not_revoked()


class TestRevokeAllRefreshTokens:
    def test_normal_revoke(self, user, other_user):
        user_tokens = [RefreshToken.for_user(user) for _ in range(2)]
        RefreshToken.for_user(other_user)

        _revoke_all_refresh_tokens(user=user)

        revoked_jtis = set(BlacklistedToken.objects.values_list('token__jti', flat=True))
        user_tokens_jtis = {str(t['jti']) for t in user_tokens}

        assert revoked_jtis == user_tokens_jtis


class TestUserResetPasswordByOldPassword:
    old_password = 'OldP@ssw0rd'
    new_password = 'NewP@ssw0rd'

    @pytest.fixture(autouse=True)
    def setup(self, user):
        user.set_password(self.old_password)
        user.save(update_fields=['password'])
        self.user = user
        self.user_tokens = [RefreshToken.for_user(user) for _ in range(2)]

    def assert_all_tokens_revoked(self):
        revoked_jtis = set(BlacklistedToken.objects.values_list('token__jti', flat=True))
        user_tokens_jtis = {str(t['jti']) for t in self.user_tokens}

        assert revoked_jtis == user_tokens_jtis

    def assert_password_changed(self):
        self.user.refresh_from_db()
        assert not self.user.check_password(self.old_password)
        assert self.user.check_password(self.new_password)

    def assert_password_not_changed(self):
        self.user.refresh_from_db()
        assert self.user.check_password(self.old_password)
        assert not self.user.check_password(self.new_password)

    def test_normal_reset(self):
        self.assert_password_not_changed()

        user_reset_password_by_old_password(
            user_id=self.user.pk, 
            old_password=self.old_password, 
            new_password=self.new_password
        )

        self.assert_password_changed()

    def test_not_existing_user(self):
        with pytest.raises(exceptions.NotFound):
            user_reset_password_by_old_password(
                user_id=-1, 
                old_password=self.old_password, 
                new_password=self.new_password
            )

        self.assert_password_not_changed()

    def test_old_password_does_not_match(self):
        with pytest.raises(PasswordsDoNotMatch):
            user_reset_password_by_old_password(
                user_id=self.user.pk, 
                old_password='WrongOldPassword', 
                new_password=self.new_password
            )

        self.assert_password_not_changed()

    def test_atomicity(self, mocker):
        old = _revoke_all_refresh_tokens

        def revoke_then_fail(*args, **kwargs):
            old(*args, **kwargs)
            raise RuntimeError

        mocker.patch(
            'apps.users.services.auth._revoke_all_refresh_tokens',
            side_effect=revoke_then_fail,
        )

        with pytest.raises(RuntimeError):
            user_reset_password_by_old_password(
                user_id=self.user.pk, 
                old_password=self.old_password, 
                new_password=self.new_password
            )

        assert BlacklistedToken.objects.count() == 0
        self.assert_password_not_changed()