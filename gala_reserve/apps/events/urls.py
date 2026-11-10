from django.urls import path

from apps.events.views.categories import (
    ListCreateCategoryView,
    RetrieveUpdateDeleteCategoryView,
)
from apps.events.views.events import ListCreateEventView, RetrieveUpdateEventView

urlpatterns = [
    path('categories/', ListCreateCategoryView.as_view(), name='list-create-category'),
    path('categories/<int:id>/', RetrieveUpdateDeleteCategoryView.as_view(), name='retrieve-update-delete-category'),
    path('events/', ListCreateEventView.as_view(), name='list-create-event'),
    path('events/<int:id>/', RetrieveUpdateEventView.as_view(), name='retrieve-update-event')
]