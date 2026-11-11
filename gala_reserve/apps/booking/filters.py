from django_filters import FilterSet

from apps.booking.models import Registration


class RegistrationFilter(FilterSet):
    class Meta:
        model = Registration
        fields = ('status', 'event')