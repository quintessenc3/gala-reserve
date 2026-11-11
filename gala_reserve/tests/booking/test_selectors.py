from apps.booking.factories import RegistrationFactory
from apps.booking.selectors import RegistrationSelector


class TestRegistrationSelector:
    def test_my_registrations_returns_only_viewers_registrations(self, user, other_user):
        my_registrations = [
            RegistrationFactory.create(user=user),
            RegistrationFactory.create(user=user),
        ]
        RegistrationFactory.create(user=other_user)

        assert set(RegistrationSelector.my_registrations(viewer=user)) == set(my_registrations)
