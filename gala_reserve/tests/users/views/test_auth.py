import random
from datetime import timedelta

import pytest
from apps.core import error_codes
from apps.users.factories import UserFactory
from apps.users.models import OneTimeCode, OneTimeCodePurpose, User
from apps.users.services.auth import otp_issue
from django.urls import reverse
from django.utils import timezone


@pytest.fixture(scope='class')
def user_otp_code(user: User) -> tuple[OneTimeCode, str | None]:
    return otp_issue(user.pk, OneTimeCodePurpose.EMAIL_VERIFICATION)


class TestRegisterView:
    payload = {
        'username': 'user', 
        'email': 'user@example.com', 
        'password': 'SDal1221WEwqe241',
        'first_name': 'John', 
        'last_name': 'Doe',
    }

    def test_success(self, transactional_db, api_client, mocker):
        send_verification_email = mocker.patch('apps.users.services.auth.send_verification_email.delay')

        response = api_client.post(reverse('register'), self.payload, format='json')

        assert response.status_code == 201
        assert User.objects.filter(email=self.payload['email']).exists()
        send_verification_email.assert_called_once()

    def test_duplicate_email_returns_400(self, api_client, user):
        payload = {**self.payload, 'email': user.email}
        response = api_client.post(reverse('register'), payload, format='json')

        assert response.status_code == 400
        assert 'email' in response.json()['error']['details']


class TestEmailVerifyView:
    @pytest.fixture(autouse=True)
    def setup(self, db, user):
        self.user = user
        self.otp, self.code = otp_issue(user.pk, OneTimeCodePurpose.EMAIL_VERIFICATION)
        self.payload = {'code': self.code}

    def test_success(self, auth_client):
        response = auth_client.post(reverse('email-verify'), self.payload, format='json')

        assert response.status_code == 200
        assert User.objects.filter(is_email_verified=True).count() == 1
        assert OneTimeCode.objects.filter(used_at__isnull=False).count() == 1

    def test_requires_authentication(self, api_client):
        response = api_client.post(reverse('email-verify'), self.payload, format='json')

        assert response.status_code == 401
        assert response.json()['error']['code'] == 'not_authenticated'

    def test_invalid_code_format_returns_400(self, auth_client):
        code = ''.join(random.choices('0123456789', k=OneTimeCode.CODE_LENGTH + 1))
        response = auth_client.post(reverse('email-verify'), {'code': code}, format='json')

        assert response.status_code == 400
        assert response.json()['error']['code'] == 'invalid'

    def test_invalid_code_returns_400(self, auth_client):
        response = auth_client.post(reverse('email-verify'), {'code': '000000'}, format='json')

        assert response.status_code == 400
        assert response.json()['error']['code'] == error_codes.INVALID_CODE

    def test_expired_code_returns_400(self, auth_client):
        self.otp.created_at = timezone.now() - OneTimeCode.TTL_MINUTES - timedelta(seconds=1)
        self.otp.save(update_fields=['created_at'])

        response = auth_client.post(reverse('email-verify'), self.payload, format='json')

        assert response.status_code == 400
        assert response.json()['error']['code'] == error_codes.CODE_EXPIRED

    def test_too_many_attempts_returns_400(self, auth_client):
        self.otp.attempts = OneTimeCode.MAX_ATTEMPTS - 1
        self.otp.save(update_fields=['attempts'])

        response = auth_client.post(reverse('email-verify'), {'code': '000000'}, format='json')

        assert response.status_code == 400
        assert response.json()['error']['code'] == error_codes.TOO_MANY_ATTEMPTS

        self.otp.refresh_from_db()
        assert self.otp.attempts == OneTimeCode.MAX_ATTEMPTS

    def test_already_verified_returns_409(self, auth_client):
        self.user.is_email_verified = True
        self.user.save(update_fields=['is_email_verified'])

        response = auth_client.post(reverse('email-verify'), self.payload, format='json')

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.ALREADY_VERIFIED

    def test_user_not_found_returns_404(self, api_client):
        other_user = UserFactory.create()
        api_client.force_authenticate(user=other_user)
        other_user.delete()

        response = api_client.post(reverse('email-verify'), self.payload, format='json')

        assert response.status_code == 404
        assert response.json()['error']['code'] == 'not_found'


class TestCodeResendView:
    def test_success(self, user, auth_client):
        response = auth_client.get(reverse('email-resend'))

        assert response.status_code == 200

    def test_requires_authentication(self, api_client):
        response = api_client.get(reverse('email-resend'))

        assert response.status_code == 401
        assert response.json()['error']['code'] == 'not_authenticated'

    def test_user_not_found_returns_404(self, db, api_client):
        other_user = UserFactory.create()
        api_client.force_authenticate(user=other_user)
        other_user.delete()

        response = api_client.get(reverse('email-resend'))
        
        assert response.status_code == 404
        assert response.json()['error']['code'] == 'not_found'

    def test_already_verified_returns_409(self, user, api_client):
        user.is_email_verified = True
        user.save()

        api_client.force_authenticate(user=user)

        response = api_client.get(reverse('email-resend'))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.ALREADY_VERIFIED


class TestRequestResetCodeView:
    def test_success(self, transactional_db, user, api_client, send_password_reset_email_mock):
        payload = {'email': user.email}

        response = api_client.post(reverse('password-reset-request'), payload, format='json')

        assert response.status_code == 202
        send_password_reset_email_mock.assert_called_once()

    def test_unexisting_user(self, transactional_db, user, api_client, send_password_reset_email_mock):
        payload = {'email': 'nonexistent@example.com'}

        response = api_client.post(reverse('password-reset-request'), payload, format='json')

        assert response.status_code == 202
        assert OneTimeCode.objects.filter(user=user, purpose=OneTimeCodePurpose.PASSWORD_RESET).count() == 0
        send_password_reset_email_mock.assert_not_called()