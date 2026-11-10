from apps.events.factories import EventFactory
from apps.events.models import EventStatus
from apps.users.factories import UserFactory
from django.urls import reverse


class TestMyProfileView:
    def test_get_success(self, user, auth_client):
        response = auth_client.get(reverse('my-profile'))
        response_body = response.json()

        assert response.status_code == 200
        assert 'id' in response_body
        assert response_body['id'] == user.pk
        assert 'password' not in response_body

    def test_patch_success(self, user, auth_client):
        payload = {
            'username': 'test_username',
            'first_name': 'TestFirstName',
            'last_name': 'TestLastName',
            'bio': 'test bio'
        }

        response = auth_client.patch(reverse('my-profile'), payload, format='json')

        assert response.status_code == 200

        user.refresh_from_db()

        for field, value in payload.items():
            assert getattr(user, field) == value

    def test_patch_unique_username_returns_400(self, user, auth_client):
        other_user = UserFactory.create(username='TestUser')

        payload = {'username': other_user.username}
        response = auth_client.patch(reverse('my-profile'), payload, format='json')

        assert response.status_code == 400
        assert response.json()['error']['code'] == 'invalid'
        user.refresh_from_db()
        assert user.username != other_user.username

    def test_requires_authentication(self, api_client):
        response = api_client.get(reverse('my-profile'))

        assert response.status_code == 401
        assert response.json()['error']['code'] == 'not_authenticated'


class TestMyEventsView:
    def test_get_success_and_is_paginated_with_only_users_events(self, user, other_user, verified_client):
        user_events = [
            EventFactory.create(user=user, status=status)
            for status in EventStatus.values
        ]
        EventFactory.create(user=other_user)
        url = reverse('my-events')

        response = verified_client.get(url)
        response_body = response.json()

        assert response.status_code == 200
        assert {'count', 'next', 'previous', 'results'} == set(response_body.keys())
        assert {event['id'] for event in response_body['results']} == {event.pk for event in user_events}

    def test_get_requires_verified_user(self, auth_client):
        response = auth_client.get(reverse('my-events'))

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'