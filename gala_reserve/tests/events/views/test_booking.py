from datetime import timedelta

import freezegun
import pytest
from apps.booking.factories import RegistrationFactory
from apps.booking.models import Registration, RegistrationStatus, Ticket, TicketStatus
from apps.core import error_codes
from apps.events.factories import EventFactory
from apps.events.models import EventStatus
from apps.users.factories import UserFactory
from django.urls import reverse
from django.utils import timezone


class TestRegisterFreeEventView:
    @pytest.fixture(autouse=True)
    def send_ticket_email_mock(self, mocker):
        return mocker.patch('apps.events.services.booking.send_ticket_email.delay')

    @staticmethod
    def get_url(event_id):
        return reverse('register-free-event', kwargs={'id': event_id})

    def test_post_success(
        self,
        transactional_db,
        user,
        verified_client,
        send_ticket_email_mock,
    ):
        with freezegun.freeze_time('2025-01-01 10:00:00'):
            event = EventFactory.create(status=EventStatus.PUBLISHED)

        with freezegun.freeze_time('2025-01-01 10:15:00'):
            response = verified_client.post(self.get_url(event.pk))
            confirmed_at = timezone.now()

        registration = Registration.objects.get(event=event, user=user)
        ticket = Ticket.objects.get(registration=registration)
        event.refresh_from_db()

        assert response.status_code == 200
        assert 'message' in response.json()
        assert registration.status == RegistrationStatus.CONFIRMED
        assert registration.confirmed_at == confirmed_at
        assert registration.user == user
        assert registration.event == event
        assert ticket.registration == registration
        assert ticket.user == user
        assert ticket.event == event
        assert ticket.status == TicketStatus.VALID
        assert ticket.used_at is None
        assert event.seats_taken == 1
        send_ticket_email_mock.assert_called_once()

    def test_post_requires_verified_user(self, auth_client):
        event = EventFactory.create(status=EventStatus.PUBLISHED)

        response = auth_client.post(self.get_url(event.pk))

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'email_not_verified'

    def test_post_nonexistent_event_returns_not_found_error_code(self, verified_client):
        response = verified_client.post(self.get_url(0))

        assert response.status_code == 404
        assert response.json()['error']['code'] == 'not_found'

    def test_post_nonexistent_user_returns_not_found_error_code(self, db, api_client):
        event = EventFactory.create(status=EventStatus.PUBLISHED)
        user = UserFactory.build(pk=-1, is_email_verified=True)
        api_client.force_authenticate(user=user)

        response = api_client.post(self.get_url(event.pk))

        assert response.status_code == 404
        assert response.json()['error']['code'] == 'not_found'

    def test_post_unpublished_event_returns_error_code(self, verified_client):
        event = EventFactory.create(status=EventStatus.CANCELLED)

        response = verified_client.post(self.get_url(event.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.EVENT_NOT_PUBLISHED

    def test_post_closed_registration_returns_error_code(self, verified_client):
        event = EventFactory.create(
            status=EventStatus.PUBLISHED,
            start_at=timezone.now() - timedelta(days=1),
        )

        response = verified_client.post(self.get_url(event.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.REGISTRATION_CLOSED

    def test_post_already_registered_returns_error_code(self, user, verified_client):
        event = EventFactory.create(status=EventStatus.PUBLISHED)
        RegistrationFactory.create(user=user, event=event)

        response = verified_client.post(self.get_url(event.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.ALREADY_REGISTERED

    def test_post_no_seats_available_returns_error_code(self, verified_client):
        event = EventFactory.create(
            status=EventStatus.PUBLISHED,
            seats_taken=100,
            capacity=100,
        )

        response = verified_client.post(self.get_url(event.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.NO_SEATS_AVAILABLE
