from django.urls import path

from apps.events.views.categories import ListCreateCategoryView


urlpatterns = [
    path('categories/', ListCreateCategoryView.as_view(), name='list-create-category')
]