import pytest
from apps.users.factories import UserFactory
from apps.users.serializers.auth import RegisterInputSerializer


class TestRegisterInputSerializer:
    @pytest.mark.parametrize(('email', 'username', 'expected_errors'), [
            ('EXISTING@example.com', 'new_user', {'email'}),
            ('new@example.com', 'EXISTING_USER', {'username'})
    ])
    def test_existing_email_and_username(self, db, email, username, expected_errors):
        UserFactory.create(email='existing@example.com', username='existing_user')
        serializer = RegisterInputSerializer(data={
            'email': email,
            'username': username,
            'password': 'SDal1221WEwqe241',
            'first_name': 'John',
            'last_name': 'Doe',
        })

        assert serializer.is_valid() == False
        assert set(serializer.errors) == expected_errors
