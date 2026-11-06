import hashlib
import hmac
import random

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import exceptions, status

from apps.core import error_codes
from apps.core.exceptions import DomainError
from apps.users.models import OneTimeCode, OneTimeCodePurpose, User
from apps.users.tasks.auth import send_password_reset_email, send_verification_email


class InvalidCodeError(DomainError):
    code = error_codes.INVALID_CODE
    message = 'Этот код неверный. Повторите попытку.'
    http_status = status.HTTP_400_BAD_REQUEST


class CodeExpiredError(DomainError):
    code = error_codes.CODE_EXPIRED
    message = 'Код истек. Запросите новый код.'
    http_status = status.HTTP_400_BAD_REQUEST


class TooManyAttempts(DomainError):
    code = error_codes.TOO_MANY_ATTEMPTS
    message = 'Для этого кода превышен лимит попыток. Запросите новый код.'
    http_status = status.HTTP_400_BAD_REQUEST


class AlreadyVerified(DomainError):
    code = error_codes.ALREADY_VERIFIED
    message = 'Этот пользователь уже верифицирован.'
    http_status = status.HTTP_409_CONFLICT


def user_register(
        *, 
        email: str, 
        username: str, 
        password: str, 
        last_name: str = '', 
        first_name: str = ''
    ) -> User:
    
    '''
    Сервис регистрации пользователя.
    '''
    
    with transaction.atomic():
        user = User(email=email, username=username, last_name=last_name, first_name=first_name)
        user.set_password(password)
        user.save()

        _, code = otp_issue(user.pk, OneTimeCodePurpose.EMAIL_VERIFICATION)

        transaction.on_commit(
            lambda: send_verification_email.delay(
                user.email, 
                code,
                int(OneTimeCode.TTL_MINUTES.total_seconds() // 60)
            )
        )

    return user


def user_email_verify(*, user_id: int, code: str):
    with transaction.atomic():
        try:
            user = User.objects.select_for_update().get(pk=user_id)
        except User.DoesNotExist:
            raise exceptions.NotFound(detail='Пользователь не найден.')

        if user.is_email_verified:
            raise AlreadyVerified

        try:
            otp = OneTimeCode.objects.select_for_update().get(
                user_id=user_id,
                purpose=OneTimeCodePurpose.EMAIL_VERIFICATION,
            )
        except OneTimeCode.DoesNotExist:
            raise InvalidCodeError

        if otp.is_expired == True:
            raise CodeExpiredError

        code_digest = hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            code.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        error = None

        if not hmac.compare_digest(otp.code_hash, code_digest):
            otp.attempts += 1
            otp.save(update_fields=['attempts'])

            if otp.is_reached_attempts_limit:
                error = TooManyAttempts()
            else:
                error = InvalidCodeError()

        else:
            otp.used_at = timezone.now()
            otp.save(update_fields=['used_at'])

            user.is_email_verified = True
            user.save(update_fields=['is_email_verified'])

    if error:
        raise error


def user_request_password_reset_code(*, email: str):
    '''
    Сервис запроса сброса пароля.
    '''

    with transaction.atomic():
        user = User.objects.select_for_update().filter(email=email).first()

        if user is not None:
            _, code = otp_issue(user_id=user.pk, purpose=OneTimeCodePurpose.PASSWORD_RESET)
            
            transaction.on_commit(
                lambda: send_password_reset_email.delay(
                    user.email,
                    code,
                    int(OneTimeCode.TTL_MINUTES.total_seconds() // 60)
                )
            )


def otp_issue(user_id: int, purpose: str) -> tuple[OneTimeCode, str | None]:
    '''
    Сервис издания одноразовых ключей.
    '''

    with transaction.atomic():
        user = User.objects.filter(pk=user_id).select_for_update().first()
        if user is None:
            return

        code = None
    
        otp = (
            OneTimeCode.objects
            .filter(user_id=user_id, used_at__isnull=True, purpose=purpose)
            .order_by('-created_at')
            .first()
        )

        code = ''.join(random.choices('0123456789', k=OneTimeCode.CODE_LENGTH))
        code_hash = hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            code.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if otp is None:
            otp = OneTimeCode.objects.create(user_id=user_id, purpose=purpose, code_hash=code_hash)
        elif otp.is_expired or otp.is_reached_attempts_limit:
            otp.code_hash = code_hash
            otp.created_at = timezone.now()
            otp.attempts = 0

            otp.save(update_fields=['code_hash', 'created_at', 'attempts'])

    return otp, code


def otp_resend(*, user_id: int) -> None:
    '''
    Сервис для повторной отправки верификационного кода.
    '''

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise exceptions.NotFound(detail='Пользователь не найден.')

    if user.is_email_verified == True:
        raise AlreadyVerified
    
    _, code = otp_issue(user_id=user_id, purpose=OneTimeCodePurpose.EMAIL_VERIFICATION)
    send_verification_email.delay(
        user.email, 
        code,
        int(OneTimeCode.TTL_MINUTES.total_seconds() // 60)
    )