from django_filters import FilterSet

from apps.booking.models import Registration, Ticket


class RegistrationFilter(FilterSet):
    class Meta:
        model = Registration
        fields = ('status', 'event')


class TicketFilter(FilterSet):
    class Meta:
        model = Ticket
        fields = ('status', 'event')