from datetime import timedelta
from uuid import uuid4

import freezegun
from apps.booking.factories import RegistrationFactory, TicketFactory
from apps.booking.models import Ticket, TicketStatus
from apps.core import error_codes
from apps.events.factories import EventFactory
from apps.events.models import EventStatus
from django.urls import reverse
from django.utils import timezone


class TestTicketUseView:
    @staticmethod
    def get_url(ticket_id):
        return reverse('use-ticket', kwargs={'id': ticket_id})

    def test_post_success(self, user, other_user, auth_client):
        now = timezone.now()
        with freezegun.freeze_time(now):
            event = EventFactory.create(
                user=user,
                status=EventStatus.PUBLISHED,
                start_at=timezone.now() + timedelta(
                    minutes=Ticket.CHECKIN_OPENS_BEFORE_MINUTES - 5
                ),
            )
            registration = RegistrationFactory.create(user=other_user, event=event)
            ticket = TicketFactory.create(registration=registration)
            created_at = ticket.created_at

        response = auth_client.post(self.get_url(ticket.pk))

        ticket.refresh_from_db()

        assert response.status_code == 200
        assert 'message' in response.json()
        assert ticket.status == TicketStatus.USED
        assert ticket.used_at is not None
        assert ticket.created_at == created_at
        assert ticket.registration == registration
        assert ticket.user == other_user
        assert ticket.event == event

    def test_post_admin_can_use_ticket(self, user, other_user, verified_client):
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        event = EventFactory.create(
            user=other_user,
            status=EventStatus.PUBLISHED,
            start_at=timezone.now() - timedelta(hours=2),
        )
        registration = RegistrationFactory.create(user=other_user, event=event)
        ticket = TicketFactory.create(registration=registration)

        response = verified_client.post(self.get_url(ticket.pk))

        assert response.status_code == 200

    def test_post_ticket_owner_not_event_owner_gets_forbidden(
        self,
        user,
        other_user,
        auth_client,
    ):
        event = EventFactory.create(user=other_user, status=EventStatus.PUBLISHED)
        registration = RegistrationFactory.create(user=user, event=event)
        ticket = TicketFactory.create(registration=registration)

        response = auth_client.post(self.get_url(ticket.pk))

        assert response.status_code == 403
        assert response.json()['error']['code'] == 'permission_denied'

    def test_post_requires_authentication(self, api_client):
        response = api_client.post(self.get_url(uuid4()))

        assert response.status_code == 401
        assert response.json()['error']['code'] == 'not_authenticated'

    def test_post_nonexistent_ticket_returns_not_found_error_code(self, verified_client):
        response = verified_client.post(self.get_url(uuid4()))

        assert response.status_code == 404
        assert response.json()['error']['code'] == 'not_found'

    def test_post_cancelled_ticket_returns_409(self, user, verified_client):
        event = EventFactory.create(user=user, status=EventStatus.PUBLISHED)
        registration = RegistrationFactory.create(user=user, event=event)
        ticket = TicketFactory.create(
            registration=registration,
            status=TicketStatus.CANCELLED,
        )

        response = verified_client.post(self.get_url(ticket.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.TICKET_CANCELLED

    def test_post_already_used_ticket_returns_409(self, user, verified_client):
        event = EventFactory.create(user=user, status=EventStatus.PUBLISHED)
        registration = RegistrationFactory.create(user=user, event=event)
        ticket = TicketFactory.create(
            registration=registration,
            status=TicketStatus.USED,
        )

        response = verified_client.post(self.get_url(ticket.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.TICKET_ALREADY_USED

    def test_post_before_checkin_opens_returns_409(self, user, verified_client):
        now = timezone.now()
        with freezegun.freeze_time(now):
            event = EventFactory.create(
                user=user,
                status=EventStatus.PUBLISHED,
                start_at=timezone.now() + timedelta(hours=3),
            )
            registration = RegistrationFactory.create(user=user, event=event)
            ticket = TicketFactory.create(registration=registration)

        response = verified_client.post(self.get_url(ticket.pk))

        assert response.status_code == 409
        assert response.json()['error']['code'] == error_codes.CHECKIN_CLOSED
