from django.db.models import Q

from apps.events.models import Event, EventStatus


class EventSelector:
    @staticmethod
    def public_events():
        return Event.objects.filter(
            ~Q(status=EventStatus.DRAFT)
        )

    @staticmethod
    def visible_to(*, viewer):
        queryset = Event.objects.select_related('category', 'user')

        if viewer.is_authenticated and viewer.is_staff:
            return queryset

        visible = ~Q(status=EventStatus.DRAFT)
        if viewer.is_authenticated:
            visible |= Q(user=viewer)
        return queryset.filter(visible)