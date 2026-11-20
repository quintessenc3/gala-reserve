from datetime import timedelta

import freezegun
import pytest
from apps.booking.factories import RegistrationFactory, TicketFactory
from apps.booking.models import (
    Registration,
    RegistrationCancelReason,
    RegistrationStatus,
    TicketStatus,
)
from apps.core import error_codes
from apps.events.factories import EventFactory
from django.urls import reverse
from django.utils import timezone


class TestCancelRegistrationView:
    @pytest.fixture(autouse=True)
    def send_registration_cancelled_email_mock(self, mocker):
        return mocker.patch(
            'apps.booking.services.registrations.send_registration_cancelled_email.delay'
        )

    @staticmethod
    def get_url(registration_id):
        return reverse('cancel-registration', kwargs={'id': registration_id})

    def test_post_success(
        self,
        transactional_db,
        user,
        verified_client,
        send_registration_cancelled_email_mock,
    ):
        with freezegun.freeze_time('2026-01-01 10:00:00'):
            event = EventFactory.create(seats_taken=1)
            confirmed_at = timezone.now()
            registration = RegistrationFactory.create(
                user=user,
                event=event,
                status=RegistrationStatus.CONFIRMED,
                confirmed_at=confirmed_at,
            )
            ticket = TicketFactory.create(registration=registration)

        with freezegun.freeze_time('2026-01-01 10:15:00'):
            cancelled_at = timezone.now()
            response = verified_client.post(self.get_url(registration.pk))

        registration.refresh_from_db()
        ticket.refresh_from_db()
        event.refresh_from_db()

        assert response.status_code == 200
        assert 'message' in response.json()
        assert registration.status == RegistrationStatus.CANCELLED
        assert registration.cancel_reason == RegistrationCancelReason.BY_USER
        assert registration.cancelled_at == cancelled_at
        assert registration.user == user
        assert registration.event == event
        assert registration.confirmed_at == confirmed_at
        assert ticket.registration == registration
        assert ticket.user == user
        assert ticket.event == event
        assert ticket.status == TicketStatus.CANCELLED
        assert ticket.used_at is None
        assert event.seats_taken == 0
        assert event.updated_at == cancelled_at
        send_registration_cancelled_email_mock.assert_called_once()

    def test_post_admin_can_cancel_registration(self, user, other_user, verified_client):
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        event = EventFactory.create(seats_taken=1)
        registration = RegistrationFactory.create(
            user=other_user,
            event=event,
            status=RegistrationStatus.CONFIRMED,
        )
        TicketFactory.create(registration=registration)

        response = verified_client.post(self.get_url(registration.pk))

        assert response.status_code == 200

    def test_post_requires_owner_or_admin(self, user, other_user, api_client):
        event = EventFactory.create(seats_taken=1)
        registration = RegistrationFactory.create(
            user=user,
            event=event,
            status=RegistrationStatus.CONFIRMED,
        )
        TicketFactory.create(registration=registration)
        other_user.is_email_verified = True
        other_user.save(update_fields=['is_email_verified'])
        api_client.force_authenticate(user=other_user)

        response = api_client.post(self.get_url(registration.pk))

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'

    def test_post_nonexistent_registration_returns_not_found_error_code(self, verified_client):
        response = verified_client.post(self.get_url(0))

        assert response.status_code == 404
        assert response.json()['error']['code'] == 'not_found'

    def test_post_cancelled_registration_returns_error_code(self, user, verified_client):
        event = EventFactory.create(seats_taken=1)
        registration = RegistrationFactory.create(
            user=user,
            event=event,
            status=RegistrationStatus.CANCELLED,
        )
        TicketFactory.create(registration=registration)

        response = verified_client.post(self.get_url(registration.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.REGISTRATION_NOT_ACTIVE

    def test_post_past_deadline_returns_error_code(self, user, verified_client):
        with freezegun.freeze_time('2026-01-01 10:00:00'):
            event = EventFactory.create(
                seats_taken=1,
                start_at=timezone.now()
                + timedelta(hours=Registration.CANCEL_DEADLINE_HOURS)
                - timedelta(seconds=1),
            )
            registration = RegistrationFactory.create(
                user=user,
                event=event,
                status=RegistrationStatus.CONFIRMED,
            )
            TicketFactory.create(registration=registration)

            response = verified_client.post(self.get_url(registration.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.CANCELLATION_DEADLINE_PASSED

    def test_post_used_ticket_returns_error_code(self, user, verified_client):
        event = EventFactory.create(seats_taken=1)
        registration = RegistrationFactory.create(
            user=user,
            event=event,
            status=RegistrationStatus.CONFIRMED,
        )
        TicketFactory.create(registration=registration, status=TicketStatus.USED)

        response = verified_client.post(self.get_url(registration.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.TICKET_ALREADY_USED
