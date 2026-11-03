from django.urls import path

from apps.users.views.auth import RegisterView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register')
]