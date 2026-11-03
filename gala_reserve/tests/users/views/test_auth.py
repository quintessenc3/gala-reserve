from apps.users.models import User
from django.urls import reverse


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

