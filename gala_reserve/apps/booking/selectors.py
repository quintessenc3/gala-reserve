from apps.booking.models import Registration, Ticket


class RegistrationSelector:
    @staticmethod
    def my_registrations(*, viewer):
        return Registration.objects.filter(user=viewer)


class TicketSelector:
    @staticmethod
    def my_tickets(*, viewer):
        return Ticket.objects.filter(user=viewer)