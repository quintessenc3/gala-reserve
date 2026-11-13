from apps.booking.models import Registration, Ticket


class RegistrationSelector:
    @staticmethod
    def my_registrations(*, viewer):
        return Registration.objects.filter(user=viewer)


class TicketSelector:
    @staticmethod
    def my_tickets(*, viewer):
        return Ticket.objects.filter(user=viewer)

    @staticmethod
    def visible_to(*, viewer):
        queryset = Ticket.objects.all()
        if viewer.is_authenticated and viewer.is_staff:
            return queryset

        return queryset.filter(user=viewer)