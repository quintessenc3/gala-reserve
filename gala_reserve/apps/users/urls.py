from django.urls import path

from apps.users.views.auth import (
    CodeResendView,
    EmailVerifyView,
    LogoutView,
    PasswordResetByCodeView,
    RegisterView,
    RequestResetCodeView,
    TokenObtainPairView,
    TokenRefreshView,
)
from apps.users.views.my_profile import (
    MyEventsView,
    MyProfileView,
    MyRegistrationsView,
    PasswordResetByOldPasswordView,
)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/email/verify', EmailVerifyView.as_view(), name='email-verify'),
    path('auth/email/resend', CodeResendView.as_view(), name='email-resend'),
    path('auth/password-reset/request', RequestResetCodeView.as_view(), name='password-reset-request'),
    path('auth/password-reset/confirm', PasswordResetByCodeView.as_view(), name='password-reset-confirm'),
    path('users/me/', MyProfileView.as_view(), name='my-profile'),
    path('users/me/password', PasswordResetByOldPasswordView.as_view(), name='my-profile-password-reset'),
    path('users/me/events/', MyEventsView.as_view(), name='my-events'),
    path('users/me/registrations/', MyRegistrationsView.as_view(), name='my-registrations')
]