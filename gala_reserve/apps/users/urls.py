from django.urls import path

from apps.users.views.auth import RegisterView, TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh')
]