from datetime import timedelta
from uuid import uuid4

import freezegun
from apps.booking.factories import RegistrationFactory, TicketFactory
from apps.booking.models import TicketStatus
from apps.core import error_codes
from apps.events.factories import EventFactory
from django.urls import reverse
from django.utils import timezone


class TestTicketUseView:
    @staticmethod
    def get_url(ticket_id):
        return reverse('use-ticket', kwargs={'id': ticket_id})

    def test_post_success(self, db, user, verified_client):
        with freezegun.freeze_time('2026-01-01 08:00:00'):
            event = EventFactory.create(start_at=timezone.now() + timedelta(hours=3))
            registration = RegistrationFactory.create(user=user, event=event)
            ticket = TicketFactory.create(registration=registration)
            created_at = ticket.created_at

        with freezegun.freeze_time('2026-01-01 10:30:00'):
            used_at = timezone.now()
            response = verified_client.post(self.get_url(ticket.pk))

        ticket.refresh_from_db()

        assert response.status_code == 200
        assert 'message' in response.json()
        assert ticket.status == TicketStatus.USED
        assert ticket.used_at == used_at
        assert ticket.created_at == created_at
        assert ticket.registration == registration
        assert ticket.user == user
        assert ticket.event == event

    def test_post_admin_can_use_ticket(self, user, other_user, verified_client):
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        event = EventFactory.create(start_at=timezone.now() - timedelta(hours=2))
        registration = RegistrationFactory.create(user=other_user, event=event)
        ticket = TicketFactory.create(registration=registration)

        response = verified_client.post(self.get_url(ticket.pk))

        assert response.status_code == 200

    def test_post_non_owner_gets_not_found(self, user, other_user, api_client):
        registration = RegistrationFactory.create(user=user)
        ticket = TicketFactory.create(registration=registration)
        other_user.is_email_verified = True
        other_user.save(update_fields=['is_email_verified'])
        api_client.force_authenticate(user=other_user)

        response = api_client.post(self.get_url(ticket.pk))

        assert response.status_code == 404
        assert response.json()['error']['code'] == 'not_found'

    def test_post_requires_authentication(self, api_client):
        response = api_client.post(self.get_url(uuid4()))

        assert response.status_code == 401
        assert response.json()['error']['code'] == 'not_authenticated'

    def test_post_nonexistent_ticket_returns_not_found_error_code(self, verified_client):
        response = verified_client.post(self.get_url(uuid4()))

        assert response.status_code == 404
        assert response.json()['error']['code'] == 'not_found'

    def test_post_cancelled_ticket_returns_409(self, user, verified_client):
        registration = RegistrationFactory.create(user=user)
        ticket = TicketFactory.create(
            registration=registration,
            status=TicketStatus.CANCELLED,
        )

        response = verified_client.post(self.get_url(ticket.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.TICKET_CANCELLED

    def test_post_already_used_ticket_returns_409(self, user, verified_client):
        registration = RegistrationFactory.create(user=user)
        ticket = TicketFactory.create(
            registration=registration,
            status=TicketStatus.USED,
        )

        response = verified_client.post(self.get_url(ticket.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.TICKET_ALREADY_USED

    def test_post_before_checkin_opens_returns_409(self, user, verified_client):
        with freezegun.freeze_time('2026-01-01 08:00:00'):
            event = EventFactory.create(start_at=timezone.now() + timedelta(hours=3))
            registration = RegistrationFactory.create(user=user, event=event)
            ticket = TicketFactory.create(registration=registration)

            response = verified_client.post(self.get_url(ticket.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.CHECKIN_CLOSED
