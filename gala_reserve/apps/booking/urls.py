from django.urls import path

from apps.booking.views.registration import CancelRegistrationView

urlpatterns = [
    path('registrations/<int:id>/cancel/', CancelRegistrationView.as_view(), name='cancel-registration')
]