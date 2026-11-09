import pytest
from apps.core import error_codes
from apps.events.factories import CategoryFactory, EventFactory
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


class TestRetrieveUpdateDeleteCategoryView:
    @pytest.fixture(autouse=True)
    def setup(self, user):
        self.category = CategoryFactory.create(user=user)
        self.payload = {'name': 'Updated category', 'description': 'Updated description'}

    def test_get_success(self, api_client):
        response = api_client.get(reverse('retrieve-update-delete-category', kwargs={'id': self.category.pk}))

        assert response.status_code == 200

    def test_patch_requires_verified_user(self, auth_client):
        response = auth_client.patch(
            reverse('retrieve-update-delete-category', kwargs={'id': self.category.pk}),
            data=self.payload,
            format='json',
        )

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'

    def test_delete_requires_verified_user(self, auth_client):
        response = auth_client.delete(
            reverse('retrieve-update-delete-category', kwargs={'id': self.category.pk})
        )

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'
        assert Category.objects.filter(pk=self.category.pk).exists()

    def test_patch_success(self, verified_client):
        response = verified_client.patch(
            reverse('retrieve-update-delete-category', kwargs={'id': self.category.pk}),
            data=self.payload,
            format='json',
        )

        assert response.status_code == 200
        assert response.json()['name'] == self.payload['name']
        assert response.json()['description'] == self.payload['description']

        self.category.refresh_from_db()
        assert self.category.name == self.payload['name']
        assert self.category.description == self.payload['description']

    def test_patch_category_owned_by_another_user_is_forbidden(self, other_user, verified_client):
        category = CategoryFactory.create(user=other_user)
        original_name = category.name
        url = reverse('retrieve-update-delete-category', kwargs={'id': category.pk})

        response = verified_client.patch(url, data=self.payload, format='json')

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'
        category.refresh_from_db()
        assert category.name == original_name

    def test_delete_category_owned_by_another_user_is_forbidden(self, other_user, verified_client):
        category = CategoryFactory.create(user=other_user)
        url = reverse('retrieve-update-delete-category', kwargs={'id': category.pk})

        response = verified_client.delete(url)

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'
        assert Category.objects.filter(pk=category.pk).exists()

    def test_delete_success(self, verified_client):
        response = verified_client.delete(
            reverse('retrieve-update-delete-category', kwargs={'id': self.category.pk})
        )

        assert response.status_code == 204
        assert not Category.objects.filter(pk=self.category.pk).exists()

    def test_delete_category_with_events_returns_conflict(self, user, verified_client):
        EventFactory.create(category=self.category, user=user)

        response = verified_client.delete(
            reverse('retrieve-update-delete-category', kwargs={'id': self.category.pk})
        )

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.CATEGORY_IN_USE
        assert Category.objects.filter(pk=self.category.pk).exists()