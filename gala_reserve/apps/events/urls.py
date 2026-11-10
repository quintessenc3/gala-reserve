from django.urls import path

from apps.events.views.categories import (
    ListCreateCategoryView,
    RetrieveUpdateDeleteCategoryView,
)
from apps.events.views.events import (
    EventCancelView,
    EventPublishView,
    ListCreateEventView,
    RetrieveUpdateEventView,
    UploadEventImageView,
)

urlpatterns = [
    path('categories/', ListCreateCategoryView.as_view(), name='list-create-category'),
    path('categories/<int:id>/', RetrieveUpdateDeleteCategoryView.as_view(), name='retrieve-update-delete-category'),
    path('events/', ListCreateEventView.as_view(), name='list-create-event'),
    path('events/<int:id>/', RetrieveUpdateEventView.as_view(), name='retrieve-update-event'),
    path('events/<int:id>/image/', UploadEventImageView.as_view(), name='upload-event-image'),
    path('events/<int:id>/publish/', EventPublishView.as_view(), name='publish-event'),
    path('events/<int:id>/cancel/', EventCancelView.as_view(), name='cancel-event')
]