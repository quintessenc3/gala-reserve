import random

import pytest
from apps.users.models import OneTimeCode
from apps.users.serializers.auth import EmailVerifyInputSerializer


class TestEmailVerifyInputSerializer:
    @pytest.mark.parametrize(('code_length', 'is_valid'), [
        (OneTimeCode.CODE_LENGTH - 1, False),
        (OneTimeCode.CODE_LENGTH, True),
        (OneTimeCode.CODE_LENGTH + 1, False)
    ])
    def test_code_regex(self, code_length, is_valid):
        code = ''.join(random.choices('0123456789', k=code_length))
        serializer = EmailVerifyInputSerializer(data={'code': code})
        assert serializer.is_valid() == is_valid
        if not is_valid:
            assert 'code' in serializer.errors