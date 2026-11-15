from apps.booking.factories import RegistrationFactory, TicketFactory
from apps.events.factories import CategoryFactory, EventFactory
from apps.events.tasks.booking import send_ticket_email
from apps.users.factories import UserFactory
from django.conf import settings


class TestSendTicketEmail:
    def test_send_ticket_email(self, db, mailoutbox):
        user = UserFactory.create(email='attendee@example.com')
        category = CategoryFactory.create(name='Концерты')
        event = EventFactory.create(
            title='Концерт классической музыки',
            address='ул. Примерная, 10',
            category=category,
        )
        registration = RegistrationFactory.create(user=user, event=event)
        ticket = TicketFactory.create(registration=registration)

        send_ticket_email(str(ticket.pk))

        assert len(mailoutbox) == 1
        mail = mailoutbox[0]
        assert mail.to == [user.email]
        assert mail.from_email == settings.DEFAULT_FROM_EMAIL
        assert mail.subject
        assert event.title in mail.body
        assert str(ticket.pk) in mail.body
        assert event.address in mail.body
