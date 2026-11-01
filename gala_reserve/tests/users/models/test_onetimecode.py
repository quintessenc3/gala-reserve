from datetime import timedelta

import freezegun
import pytest
from apps.users.factories import OneTimeCodeFactory
from apps.users.models import OneTimeCode
from django.core.exceptions import ValidationError
from django.utils import timezone


@pytest.fixture
def otp() -> OneTimeCode:
    return OneTimeCodeFactory.build(user=None)

@pytest.fixture
def otp_with_user() -> OneTimeCode:
    return OneTimeCodeFactory.create()


def test_normal_otp_full_clean(db, otp: OneTimeCode):
    otp.full_clean(exclude={'user'})


def test_otc_valid_purpose_constraint(db, otp: OneTimeCode):
    otp.purpose = 'none'
    with pytest.raises(ValidationError):
        otp.validate_constraints(exclude={'user'})


def test_is_expired_property(otp: OneTimeCode):
    with freezegun.freeze_time('2015-07-10 12:00:00'):
        created_at = timezone.now() - OneTimeCode.TTL_MINUTES

        otp.created_at = created_at
        assert not otp.is_expired

        otp.created_at += timedelta(seconds=1)
        assert otp.is_expired


def test_is_exceeded_attempts_limit_property(otp: OneTimeCode):
    otp.attempts = 0
    assert not otp.is_reached_attempts_limit

    otp.attempts = otp.MAX_ATTEMPTS
    assert otp.is_reached_attempts_limit

    otp.attempts = otp.MAX_ATTEMPTS + 1
    assert otp.is_reached_attempts_limit