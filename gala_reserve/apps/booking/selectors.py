from apps.booking.models import Registration


class RegistrationSelector:
    @staticmethod
    def my_registrations(*, viewer):
        return Registration.objects.filter(user=viewer)