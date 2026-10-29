import os
import sys

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/v1/', include('apps.users.urls'))
]

TESTING = "test" in sys.argv or "PYTEST_VERSION" in os.environ

if not TESTING and settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns = [
        *urlpatterns,
    ] + debug_toolbar_urls()
