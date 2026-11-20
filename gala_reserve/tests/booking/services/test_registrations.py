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
from apps.booking.services.registrations import (
    CancellationDeadlinePassed,
    RegistrationNotActiveError,
    TicketAlreadyUsedError,
    registration_cancel,
)
from apps.events.factories import EventFactory
from apps.events.models import Event
from django.utils import timezone
from rest_framework import exceptions


class TestRegistrationCancel:
    @pytest.fixture(autouse=True)
    def send_registration_cancelled_email_mock(self, mocker):
        return mocker.patch(
            'apps.booking.services.registrations.send_registration_cancelled_email.delay'
        )

    def test_normal_cancel(
        self,
        transactional_db,
        send_registration_cancelled_email_mock,
    ):
        event = EventFactory.create(seats_taken=1)
        registration = RegistrationFactory.create(
            event=event,
            status=RegistrationStatus.CONFIRMED,
        )
        ticket = TicketFactory.create(registration=registration)
        confirmed_at = timezone.now()
        registration.confirmed_at = confirmed_at
        registration.save(update_fields=['confirmed_at'])
        event_updated_at = event.updated_at
        cancelled_at = event_updated_at + timedelta(minutes=1)

        with freezegun.freeze_time(cancelled_at):
            cancelled_registration = registration_cancel(reg_id=registration.pk)

        registration.refresh_from_db()
        ticket.refresh_from_db()
        event.refresh_from_db()

        assert cancelled_registration.pk == registration.pk
        assert registration.status == RegistrationStatus.CANCELLED
        assert registration.cancel_reason == RegistrationCancelReason.BY_USER
        assert registration.cancelled_at == cancelled_at
        assert registration.confirmed_at == confirmed_at
        assert ticket.status == TicketStatus.CANCELLED
        assert ticket.used_at is None
        assert event.seats_taken == 0
        assert event.updated_at == cancelled_at
        send_registration_cancelled_email_mock.assert_called_once_with(registration.pk)

    def test_registration_does_not_exist(
        self,
        transactional_db,
        send_registration_cancelled_email_mock,
    ):
        with pytest.raises(exceptions.NotFound):
            registration_cancel(reg_id=-1)

        send_registration_cancelled_email_mock.assert_not_called()

    def test_registration_is_already_cancelled(
        self,
        transactional_db,
        send_registration_cancelled_email_mock,
    ):
        registration = RegistrationFactory.create(status=RegistrationStatus.CANCELLED)

        with pytest.raises(RegistrationNotActiveError):
            registration_cancel(reg_id=registration.pk)

        send_registration_cancelled_email_mock.assert_not_called()

    def test_cancellation_deadline_has_passed(
        self,
        transactional_db,
        send_registration_cancelled_email_mock,
    ):
        now = timezone.now()
        event = EventFactory.create(
            seats_taken=1,
            start_at=now + timedelta(hours=Registration.CANCEL_DEADLINE_HOURS)
            - timedelta(microseconds=1),
        )
        registration = RegistrationFactory.create(
            event=event,
            status=RegistrationStatus.CONFIRMED,
        )
        ticket = TicketFactory.create(registration=registration)

        with freezegun.freeze_time(now), pytest.raises(CancellationDeadlinePassed):
            registration_cancel(reg_id=registration.pk)

        registration.refresh_from_db()
        ticket.refresh_from_db()
        event.refresh_from_db()

        assert registration.status == RegistrationStatus.CONFIRMED
        assert ticket.status == TicketStatus.VALID
        assert event.seats_taken == 1
        send_registration_cancelled_email_mock.assert_not_called()

    def test_ticket_has_already_been_used(
        self,
        transactional_db,
        send_registration_cancelled_email_mock,
    ):
        event = EventFactory.create(seats_taken=1)
        registration = RegistrationFactory.create(
            event=event,
            status=RegistrationStatus.CONFIRMED,
        )
        ticket = TicketFactory.create(
            registration=registration,
            status=TicketStatus.USED,
        )

        with pytest.raises(TicketAlreadyUsedError):
            registration_cancel(reg_id=registration.pk)

        registration.refresh_from_db()
        ticket.refresh_from_db()
        event.refresh_from_db()

        assert registration.status == RegistrationStatus.CONFIRMED
        assert ticket.status == TicketStatus.USED
        assert event.seats_taken == 1
        send_registration_cancelled_email_mock.assert_not_called()

    def test_cancellation_at_deadline_is_allowed(
        self,
        transactional_db,
        send_registration_cancelled_email_mock,
    ):
        with freezegun.freeze_time('2026-01-01 12:00:00'):
            now = timezone.now()
            event = EventFactory.create(
                seats_taken=1,
                start_at=now + timedelta(hours=Registration.CANCEL_DEADLINE_HOURS),
            )
            registration = RegistrationFactory.create(
                event=event,
                status=RegistrationStatus.CONFIRMED,
            )
            TicketFactory.create(registration=registration)

            registration_cancel(reg_id=registration.pk)

        registration.refresh_from_db()
        assert registration.status == RegistrationStatus.CANCELLED
        send_registration_cancelled_email_mock.assert_called_once_with(registration.pk)

    def test_pending_registration_can_be_cancelled_inside_deadline(
        self,
        transactional_db,
        send_registration_cancelled_email_mock,
    ):
        with freezegun.freeze_time('2026-01-01 12:00:00'):
            event = EventFactory.create(
                seats_taken=1,
                start_at=timezone.now() + timedelta(hours=1),
            )
            registration = RegistrationFactory.create(
                event=event,
                status=RegistrationStatus.PENDING,
            )
            TicketFactory.create(registration=registration)

            registration_cancel(reg_id=registration.pk)

        registration.refresh_from_db()
        assert registration.status == RegistrationStatus.CANCELLED
        send_registration_cancelled_email_mock.assert_called_once_with(registration.pk)

    def test_atomicity_when_event_save_fails(
        self,
        transactional_db,
        mocker,
        send_registration_cancelled_email_mock,
    ):
        event = EventFactory.create(seats_taken=1)
        registration = RegistrationFactory.create(
            event=event,
            status=RegistrationStatus.CONFIRMED,
        )
        ticket = TicketFactory.create(registration=registration)
        original_save = Event.save

        def save_then_fail(self, *args, **kwargs):
            original_save(self, *args, **kwargs)
            raise RuntimeError

        event_save_mock = mocker.patch.object(
            Event,
            'save',
            autospec=True,
            side_effect=save_then_fail,
        )

        with pytest.raises(RuntimeError):
            registration_cancel(reg_id=registration.pk)

        event_save_mock.assert_called_once()
        registration.refresh_from_db()
        ticket.refresh_from_db()
        event.refresh_from_db()

        assert registration.status == RegistrationStatus.CONFIRMED
        assert registration.cancel_reason == ''
        assert registration.cancelled_at is None
        assert ticket.status == TicketStatus.VALID
        assert event.seats_taken == 1
        send_registration_cancelled_email_mock.assert_not_called()
