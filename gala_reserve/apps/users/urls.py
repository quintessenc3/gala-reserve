from django.urls import path

from apps.users.views.auth import RegisterView, TokenObtainPairView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token'),
]