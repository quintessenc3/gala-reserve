from django.db.models import Q

from apps.events.models import Event, EventStatus


class EventSelector:
    @staticmethod
    def public_events():
        return Event.objects.filter(
            ~Q(status=EventStatus.DRAFT)
        )