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


@pytest.mark.parametrize('delta, expected', [
        (timedelta(seconds=-1), False),
        (timedelta(seconds=0), True),
        (timedelta(seconds=1), True),
    ],
)
def test_is_expired(delta, expected, otp):
    created_at = timezone.now()
    expires_at = created_at + OneTimeCode.TTL_MINUTES

    with freezegun.freeze_time(expires_at + delta):
        assert otp.is_expired is expected


def test_is_exceeded_attempts_limit_property(otp: OneTimeCode):
    otp.attempts = 0
    assert not otp.is_reached_attempts_limit

    otp.attempts = otp.MAX_ATTEMPTS
    assert otp.is_reached_attempts_limit

    otp.attempts = otp.MAX_ATTEMPTS + 1
    assert otp.is_reached_attempts_limit