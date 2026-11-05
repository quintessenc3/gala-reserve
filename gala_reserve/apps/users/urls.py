from django.urls import path

from apps.users.views.auth import (
    EmailVerifyView,
    RegisterView,
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/email/verify', EmailVerifyView.as_view(), name='email-verify')
]