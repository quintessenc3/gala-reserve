from celery import shared_task
from django.db.models.functions import Now

from apps.events.models import Event, EventStatus


@shared_task
def complete_finished_events() -> None:
    (
        Event.objects
        .filter(end_at__lte=Now(), status=EventStatus.PUBLISHED)
        .update(status=EventStatus.COMPLETED, updated_at=Now())
    )