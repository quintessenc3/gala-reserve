from datetime import timedelta

import pytest
from apps.events.factories import CategoryFactory, EventFactory
from apps.events.models import Event, EventStatus
from django.urls import reverse
from django.utils import timezone


class TestListCreateEventView:
    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.category = CategoryFactory.create()
        self.payload = {
            'title': 'New event',
            'description': 'Description for the new event',
            'category': self.category.pk,
            'address': '123 Example Street',
            'start_at': timezone.now() + timedelta(days=7),
            'end_at': timezone.now() + timedelta(days=8),
            'capacity': 100,
            'price': '25.00',
            'status': EventStatus.DRAFT,
        }
        self.url = reverse('list-create-event')

    def test_get_success_and_is_paginated(self, api_client):
        EventFactory.create(status=EventStatus.PUBLISHED)

        response = api_client.get(self.url)

        assert response.status_code == 200
        assert {'count', 'next', 'previous', 'results'} == set(response.json().keys())
        assert response.json()['count'] == 1
        assert len(response.json()['results']) == 1

    def test_get_returns_only_events_not_in_draft_status(self, api_client):
        published_event = EventFactory.create(status=EventStatus.PUBLISHED)
        completed_event = EventFactory.create(status=EventStatus.COMPLETED)
        cancelled_event = EventFactory.create(status=EventStatus.CANCELLED)
        EventFactory.create(status=EventStatus.DRAFT)

        response = api_client.get(self.url)

        assert response.status_code == 200
        result_ids = {event['id'] for event in response.json()['results']}
        assert result_ids == {
            published_event.pk,
            completed_event.pk,
            cancelled_event.pk,
        }

    @pytest.mark.parametrize('search_field', ('title', 'description', 'address'))
    def test_search_filter_is_case_insensitive(self, api_client, search_field):
        event_values = {
            'title': 'Different title',
            'description': 'Different description',
            'address': 'Different address',
        }
        event_values[search_field] = 'MixedCaseSearchTerm'
        event = EventFactory.create(status=EventStatus.PUBLISHED, **event_values)
        EventFactory.create(
            status=EventStatus.PUBLISHED,
            title='Another title',
            description='Another description',
            address='Another address',
        )

        response = api_client.get(self.url, data={'search': 'mixedcasesearchterm'})

        assert response.status_code == 200
        results = response.json()['results']
        assert len(results) == 1
        assert results[0]['id'] == event.pk

    def test_post_requires_verified_user(self, auth_client):
        response = auth_client.post(self.url, data=self.payload, format='json')

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'

    def test_post_success(self, user, verified_client):
        response = verified_client.post(self.url, data=self.payload, format='json')

        assert response.status_code == 201
        assert Event.objects.count() == 1
        event = Event.objects.get()
        assert event.user == user
        assert event.category == self.category
        assert event.title == self.payload['title']
        assert event.status == EventStatus.DRAFT
        assert response.json()['id'] == event.pk
