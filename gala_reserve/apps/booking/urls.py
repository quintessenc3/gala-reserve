from django.urls import path

from apps.booking.views.registration import CancelRegistrationView
from apps.booking.views.tickets import TicketUseView

urlpatterns = [
    path('registrations/<int:id>/cancel/', CancelRegistrationView.as_view(), name='cancel-registration'),
    path('tickets/<uuid:id>/use/', TicketUseView.as_view(), name='use-ticket')
]