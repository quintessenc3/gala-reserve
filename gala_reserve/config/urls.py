import os
import sys

from apps.core.exceptions import django_exc_handler_stub
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

handler404 = django_exc_handler_stub
handler500 = django_exc_handler_stub

urlpatterns = [
    path('admin/', admin.site.urls),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    path('', include('apps.users.urls')),
    path('', include('apps.events.urls')),
    path('', include('apps.booking.urls'))
]

TESTING = "test" in sys.argv or "PYTEST_VERSION" in os.environ

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    if not TESTING:
        from debug_toolbar.toolbar import debug_toolbar_urls

        urlpatterns = [
            *urlpatterns,
        ] + debug_toolbar_urls()
