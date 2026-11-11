import pytest
from apps.booking.factories import RegistrationFactory, TicketFactory
from apps.booking.models import RegistrationStatus
from apps.events.factories import EventFactory
from apps.users.factories import UserFactory
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError


class TestRegistration:
    def test_normal_registration(self, db):
        registration = RegistrationFactory.create()

        assert registration.status == RegistrationStatus.PENDING

    def test_user_cannot_be_deleted_with_registration(self, db):
        registration = RegistrationFactory.create()

        with pytest.raises(ProtectedError):
            registration.user.delete()

    def test_event_cannot_be_deleted_with_registration(self, db):
        registration = RegistrationFactory.create()

        with pytest.raises(ProtectedError):
            registration.event.delete()

    @pytest.mark.parametrize(('existing_status', 'new_status'), [
            (RegistrationStatus.PENDING, RegistrationStatus.PENDING),
            (RegistrationStatus.PENDING, RegistrationStatus.CONFIRMED),
            (RegistrationStatus.CONFIRMED, RegistrationStatus.PENDING),
            (RegistrationStatus.CONFIRMED, RegistrationStatus.CONFIRMED),
        ],
    )
    def test_unique_active_user_event_constraint(self, db, existing_status, new_status):
        registration = RegistrationFactory.create(status=existing_status)

        with pytest.raises(IntegrityError):
            RegistrationFactory.create(
                user=registration.user,
                event=registration.event,
                status=new_status,
            )

    def test_cancelled_registration_does_not_violate_unique_active_user_event_constraint(self, user):
        event = EventFactory.create()

        RegistrationFactory.create(
            user=user,
            event=event,
            status=RegistrationStatus.CANCELLED
        )

        RegistrationFactory.create(
            user=user,
            event=event,
            status=RegistrationStatus.CONFIRMED,
        )


class TestTicket:
    def test_normal_ticket(self, db):
        TicketFactory.create()

    def test_registration_cannot_be_deleted_with_ticket(self, db):
        ticket = TicketFactory.create()

        with pytest.raises(ProtectedError):
            ticket.registration.delete()

    def test_user_cannot_be_deleted_with_ticket(self, db):
        registration = RegistrationFactory.create()
        ticket = TicketFactory.create(
            registration=registration,
            user=UserFactory.create(),
        )

        with pytest.raises(ProtectedError):
            ticket.user.delete()

    def test_event_cannot_be_deleted_with_ticket(self, db):
        registration = RegistrationFactory.create()
        ticket = TicketFactory.create(
            registration=registration,
            event=EventFactory.create(),
        )

        with pytest.raises(ProtectedError):
            ticket.event.delete()
