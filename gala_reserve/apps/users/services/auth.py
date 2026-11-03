import hashlib
import hmac
import random

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.users.models import OneTimeCode, OneTimeCodePurpose, User
from apps.users.tasks.auth import send_verification_email


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