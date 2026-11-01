import hashlib
from datetime import timedelta

import factory
from django.utils import timezone

from apps.users.models import OneTimeCode, OneTimeCodePurpose, User

USER_TEST_PASSWORD = 'P@ssw0rd'


class UserFactory(factory.django.DjangoModelFactory):
    '''
    Фабрика User.
    '''

    username = factory.Sequence(lambda n: f'user_{n}')
    password = factory.django.Password(password=USER_TEST_PASSWORD)
    email = factory.Sequence(lambda n: f'user{n}@example.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    bio = factory.Faker('text')
    photo = factory.django.ImageField()
    is_email_verified = False
    is_active = True
    is_staff = False

    class Meta:
        model = User


class OneTimeCodeFactory(factory.django.DjangoModelFactory):
    '''
    Фабрика OneTimeCode.
    '''

    user = factory.SubFactory(UserFactory)
    purpose = OneTimeCodePurpose.EMAIL_VERIFICATION
    code_hash = factory.LazyAttribute(
        lambda obj: hashlib.md5(
            obj.raw_code.encode('utf-8')
        ).hexdigest()
    )
    used_at = None
    attempts = 0

    class Meta:
        model = OneTimeCode

    class Params:
        raw_code = '123456'