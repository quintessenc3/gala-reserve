from apps.booking.factories import RegistrationFactory, TicketFactory
from apps.booking.selectors import RegistrationSelector, TicketSelector


class TestRegistrationSelector:
    def test_my_registrations_returns_only_viewers_registrations(self, user, other_user):
        my_registrations = [
            RegistrationFactory.create(user=user),
            RegistrationFactory.create(user=user),
        ]
        RegistrationFactory.create(user=other_user)

        assert set(RegistrationSelector.my_registrations(viewer=user)) == set(my_registrations)


class TestTicketSelector:
    def test_my_tickets_returns_only_viewers_tickets(self, user, other_user):
        my_tickets = [
            TicketFactory.create(registration=RegistrationFactory.create(user=user)),
            TicketFactory.create(registration=RegistrationFactory.create(user=user)),
        ]
        TicketFactory.create(registration=RegistrationFactory.create(user=other_user))

        assert set(TicketSelector.my_tickets(viewer=user)) == set(my_tickets)

    def test_visible_to_returns_only_viewers_tickets(self, user, other_user):
        my_tickets = [
            TicketFactory.create(registration=RegistrationFactory.create(user=user)),
            TicketFactory.create(registration=RegistrationFactory.create(user=user)),
        ]
        TicketFactory.create(registration=RegistrationFactory.create(user=other_user))

        assert set(TicketSelector.visible_to(viewer=user)) == set(my_tickets)

    def test_visible_to_returns_all_tickets_for_admins(self, user, other_user):
        user.is_staff = True
        tickets = [
            TicketFactory.create(registration=RegistrationFactory.create(user=user)),
            TicketFactory.create(registration=RegistrationFactory.create(user=other_user)),
        ]

        assert set(TicketSelector.visible_to(viewer=user)) == set(tickets)
