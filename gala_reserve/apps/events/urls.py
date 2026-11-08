from django.urls import path

from apps.events.views.categories import (
    ListCreateCategoryView,
    RetrieveUpdateDeleteCategoryView,
)

urlpatterns = [
    path('categories/', ListCreateCategoryView.as_view(), name='list-create-category'),
    path('categories/<int:id>/', RetrieveUpdateDeleteCategoryView.as_view(), name='retrieve-update-delete-category')
]