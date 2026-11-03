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
        )

        if otp is None:
            otp = OneTimeCode.objects.create(user_id=user_id, purpose=purpose, code_hash=code_hash)
        elif otp.is_expired or otp.is_reached_attempts_limit:
            otp.code_hash = otp.code_hash
            otp.created_at = timezone.now()
            otp.attempts = 0

            otp.save(update_fields=['code_hash', 'created_at', 'attempts'])

    return otp, code


"""def user_verify(user_id: int, code: str) -> User:
    '''
    Сервис для подтверждения учетной записи пользователя
    через верификационный код.
    '''

    user = (
        User.objects
        .select_related('verification_code')
        .get(pk=user_id)
    )

    if user.is_verified:
        raise ValidationError('Учетная запись с этой электронной почтой уже верифицирована.')

    try:
        verification_code = user.verification_code
    except User.verification_code.RelatedObjectDoesNotExist:
        raise ValidationError('Для этой учетной записи не был отправлен верификационный код.')
    
    if verification_code.is_expired:
        raise ValidationError('Код истек. Запросите новый код.')

    if verification_code.code != code:
        raise ValidationError('Неверный код. Повторите попытку.')

    user.is_verified = True
    user.save()
    
    return user


def otp_generate(user_id: int) -> OneTimeCode:
    '''
    Сервис для создания или получения существующего верификационного кода.
    Если код истекший, он автоматически обновляется.
    '''

    code = ''.join(random.choices('0123456789', k=VerificationCode.CODE_LENGTH))
    verification_code, _ = VerificationCode.objects.get_or_create(
        user_id=user.pk, 
        defaults={'user': user, 'code': code}
    )

    if verification_code.is_expired:
        verification_code.code = code
        verification_code.expires_at = timezone.now() + VerificationCode.CODE_LIFETIME
        verification_code.save()

    return verification_code


def send_verification_email(email: str, code: str, seconds_left: int) -> None:
    '''
    Сервис для отправки письма с кодом для верификации.
    '''

    send_mail(
        subject='Верификационный код Cosmos API',
        message=f'Ваш верификационный код: {code}. Он истекает через {int(seconds_left / 60)} минут.',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[email]
    )


def user_change_password(user: User, password: str) -> User:
    '''
    Сервис смены пароля.
    '''

    if user.check_password(password):
        raise ValidationError('Пароль совпадает с текущим. Выберите другой пароль.')

    user.set_password(password)
    user.save()

    return user"""