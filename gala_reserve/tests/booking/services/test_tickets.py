from datetime import timedelta
from uuid import uuid4

import freezegun
import pytest
from apps.booking.factories import RegistrationFactory, TicketFactory
from apps.booking.models import Ticket, TicketStatus
from apps.booking.services.tickets import (
    CheckInClosedError,
    TicketAlreadyUsedError,
    TicketCancelledError,
    ticket_use,
)
from apps.events.factories import EventFactory
from apps.events.models import EventStatus
from django.utils import timezone
from rest_framework import exceptions


class TestTicketUse:
    def test_normal_use_updates_ticket_fields(self, db, user):
        with freezegun.freeze_time('2026-01-01 08:00:00'):
            event = EventFactory.create(
                status=EventStatus.PUBLISHED,
                start_at=timezone.now() + timedelta(hours=3),
            )
            registration = RegistrationFactory.create(user=user, event=event)
            ticket = TicketFactory.create(registration=registration)
            created_at = ticket.created_at

        with freezegun.freeze_time('2026-01-01 10:30:00'):
            used_at = timezone.now()
            used_ticket = ticket_use(ticket_id=str(ticket.pk))

        ticket.refresh_from_db()

        assert used_ticket.pk == ticket.pk
        assert ticket.status == TicketStatus.USED
        assert ticket.used_at == used_at
        assert ticket.created_at == created_at

    def test_ticket_does_not_exist(self, db):
        with pytest.raises(exceptions.NotFound):
            ticket_use(ticket_id=str(uuid4()))

    def test_cancelled_ticket_cannot_be_used(self, db):
        event = EventFactory.create(status=EventStatus.PUBLISHED)
        registration = RegistrationFactory.create(event=event)
        ticket = TicketFactory.create(
            registration=registration,
            status=TicketStatus.CANCELLED,
        )

        with pytest.raises(TicketCancelledError):
            ticket_use(ticket_id=str(ticket.pk))

        ticket.refresh_from_db()
        assert ticket.status == TicketStatus.CANCELLED
        assert ticket.used_at is None

    def test_already_used_ticket_cannot_be_used_again(self, db):
        event = EventFactory.create(status=EventStatus.PUBLISHED)
        registration = RegistrationFactory.create(event=event)
        ticket = TicketFactory.create(
            registration=registration,
            status=TicketStatus.USED,
        )

        with pytest.raises(TicketAlreadyUsedError):
            ticket_use(ticket_id=str(ticket.pk))

        ticket.refresh_from_db()
        assert ticket.status == TicketStatus.USED

    @pytest.mark.parametrize(
        'status',
        (EventStatus.DRAFT, EventStatus.COMPLETED, EventStatus.CANCELLED),
    )
    def test_event_not_published_cannot_be_used(self, db, status):
        event = EventFactory.create(status=status)
        registration = RegistrationFactory.create(event=event)
        ticket = TicketFactory.create(registration=registration)

        with pytest.raises(CheckInClosedError):
            ticket_use(ticket_id=str(ticket.pk))

        ticket.refresh_from_db()
        assert ticket.status == TicketStatus.VALID
        assert ticket.used_at is None

    def test_checkin_is_closed_before_opening_boundary(self, db, user):
        with freezegun.freeze_time('2026-01-01 08:00:00'):
            event = EventFactory.create(
                status=EventStatus.PUBLISHED,
                start_at=timezone.now() + timedelta(hours=3),
            )
            registration = RegistrationFactory.create(user=user, event=event)
            ticket = TicketFactory.create(registration=registration)

        checkin_opens_at = event.start_at - timedelta(
            minutes=Ticket.CHECKIN_OPENS_BEFORE_MINUTES
        )
        with (
            freezegun.freeze_time(checkin_opens_at - timedelta(seconds=1)),
            pytest.raises(CheckInClosedError),
        ):
            ticket_use(ticket_id=str(ticket.pk))

        ticket.refresh_from_db()
        assert ticket.status == TicketStatus.VALID
        assert ticket.used_at is None

    def test_checkin_opens_at_boundary(self, db, user):
        with freezegun.freeze_time('2026-01-01 08:00:00'):
            event = EventFactory.create(
                status=EventStatus.PUBLISHED,
                start_at=timezone.now() + timedelta(hours=3),
            )
            registration = RegistrationFactory.create(user=user, event=event)
            ticket = TicketFactory.create(registration=registration)

        checkin_opens_at = event.start_at - timedelta(
            minutes=Ticket.CHECKIN_OPENS_BEFORE_MINUTES
        )
        with freezegun.freeze_time(checkin_opens_at):
            used_ticket = ticket_use(ticket_id=str(ticket.pk))

        ticket.refresh_from_db()
        assert used_ticket.pk == ticket.pk
        assert ticket.status == TicketStatus.USED
        assert ticket.used_at == checkin_opens_at
