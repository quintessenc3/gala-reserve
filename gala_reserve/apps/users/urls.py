from django.urls import path

from apps.users.views.auth import (
    CodeResendView,
    EmailVerifyView,
    LogoutView,
    RegisterView,
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/email/verify', EmailVerifyView.as_view(), name='email-verify'),
    path('auth/email/resend', CodeResendView.as_view(), name='email-resend')
]