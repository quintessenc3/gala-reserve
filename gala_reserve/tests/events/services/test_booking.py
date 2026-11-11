from datetime import timedelta

import freezegun
import pytest
from apps.booking.factories import RegistrationFactory
from apps.booking.models import Registration, RegistrationStatus, Ticket, TicketStatus
from apps.events.factories import EventFactory
from apps.events.models import EventStatus
from apps.events.services.booking import (
    AlreadyRegisteredError,
    EventNotPublishedError,
    NoSeatsAvailableError,
    RegistrationClosedError,
    _try_register,
    book_free_event,
)
from django.db import transaction
from django.utils import timezone
from rest_framework import exceptions


class TestTryRegister:
    @pytest.fixture(autouse=True)
    def setup(self, user):
        self.user = user
        self.event = EventFactory.create(status=EventStatus.PUBLISHED)

    def test_normal_register(self):
        with transaction.atomic():
            event, user, registration = _try_register(
                event_id=self.event.pk,
                user_id=self.user.pk,
            )

        assert Registration.objects.count() == 1
        assert registration.event == event == self.event
        assert registration.user == user == self.user
        assert registration.status == RegistrationStatus.PENDING

    def test_event_does_not_exist(self):
        with pytest.raises(exceptions.NotFound), transaction.atomic():
            _try_register(event_id=-1, user_id=self.user.pk)

    def test_user_does_not_exist(self):
        with pytest.raises(exceptions.NotFound), transaction.atomic():
            _try_register(event_id=self.event.pk, user_id=-1)

    def test_event_is_not_published(self):
        self.event.status = EventStatus.DRAFT
        self.event.published_at = None
        self.event.save(update_fields=['status', 'published_at'])

        with pytest.raises(EventNotPublishedError), transaction.atomic():
            _try_register(event_id=self.event.pk, user_id=self.user.pk)

    def test_registration_is_closed(self):
        self.event.start_at = timezone.now() - timedelta(days=1)
        self.event.save(update_fields=['start_at'])

        with pytest.raises(RegistrationClosedError), transaction.atomic():
            _try_register(event_id=self.event.pk, user_id=self.user.pk)

    def test_no_seats_are_available(self):
        self.event.seats_taken = self.event.capacity
        self.event.save(update_fields=['seats_taken'])

        with pytest.raises(NoSeatsAvailableError), transaction.atomic():
            _try_register(event_id=self.event.pk, user_id=self.user.pk)

    def test_user_is_already_registered(self):
        RegistrationFactory.create(user=self.user, event=self.event)

        with pytest.raises(AlreadyRegisteredError), transaction.atomic():
            _try_register(event_id=self.event.pk, user_id=self.user.pk)


class TestBookFreeEvent:
    def test_normal_book(self, transactional_db, user, mocker):
        send_ticket_email_mock = mocker.patch(
            'apps.events.services.booking.send_ticket_email.delay'
        )

        with freezegun.freeze_time('2016-01-01 12:00:00'):
            event = EventFactory.create(status=EventStatus.PUBLISHED)

        with freezegun.freeze_time('2016-01-01 12:15:00'):
            update_time = timezone.now()
            book_free_event(event_id=event.pk, user_id=user.pk)

        registration = Registration.objects.get(event=event, user=user)
        ticket = Ticket.objects.get(
            user=user,
            registration=registration,
            event=event
        )
        event.refresh_from_db()

        assert registration.confirmed_at == update_time

        assert registration.status == RegistrationStatus.CONFIRMED
        assert registration.confirmed_at is not None
        assert event.seats_taken == 1
        assert ticket.used_at is None
        assert ticket.status == TicketStatus.VALID
        send_ticket_email_mock.assert_called_once()

    def test_atomicity(self, user, mocker):
        with freezegun.freeze_time('2016-01-01 12:00:00'):
            event_create_time = timezone.now()
            event = EventFactory.create(status=EventStatus.PUBLISHED)

        original_save = Ticket.save

        def _save_then_fail(self, *args, **kwargs):
            original_save(self, *args, **kwargs)
            raise RuntimeError

        mocker.patch.object(Ticket, 'save', autospec=True, side_effect=_save_then_fail)

        with pytest.raises(RuntimeError), freezegun.freeze_time('2016-01-01 12:15:00'):
            book_free_event(event_id=event.pk, user_id=user.pk)

        event.refresh_from_db()
        assert not Registration.objects.filter(event=event, user=user).exists()
        assert not Ticket.objects.filter(event=event, user=user).exists()
        assert event.seats_taken == 0
        assert event.updated_at == event_create_time