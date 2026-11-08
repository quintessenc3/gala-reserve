import pytest
from apps.events.factories import CategoryFactory
from apps.events.models import Category
from django.urls import reverse


class TestListCreateCategoryView:
    @pytest.fixture(autouse=True)
    def setup(self, user):
        self.payload = {
            'name': 'Category name',
            'description': 'Category description',
            'user': user.pk
        }

    def test_get_success(self, api_client):
        response = api_client.get(reverse('list-create-category'))

        assert response.status_code == 200
        assert {'count', 'next', 'previous', 'results'} == set(response.json().keys())

    def test_search_filter(self, api_client):
        CategoryFactory.create(name='Concerts')
        CategoryFactory.create(name='Birthdays')

        response = api_client.get(reverse('list-create-category'), data={'search': 'birt'})
        assert response.status_code == 200

        response_data = response.json()
        assert len(response_data['results']) == 1
        assert response_data['results'][0]['name'] == 'Birthdays'

    def test_post_requires_verified_user(self, auth_client):
        response = auth_client.post(reverse('list-create-category'), data=self.payload, format='json')

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'

    def test_post_success(self, user, verified_client):
        response = verified_client.post(
            reverse('list-create-category'), 
            data=self.payload, 
            format='json'
        )

        assert response.status_code == 201
        assert Category.objects.count() == 1
        assert Category.objects.first().user == user

    def test_case_insensitive_duplicated_returns_400(self, verified_client):
        CategoryFactory.create(name='Concerts')
        payload = {**self.payload, 'name': 'concerts'}

        response = verified_client.post(
            reverse('list-create-category'), 
            data=payload, 
            format='json'
        )

        assert response.status_code == 400
        assert response.json()['error']['code'] == 'invalid'