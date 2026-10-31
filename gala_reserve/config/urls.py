import os
import sys

from apps.core.exceptions import django_exc_handler_stub
from django.conf import settings
from django.contrib import admin
from django.urls import path

handler404 = django_exc_handler_stub
handler500 = django_exc_handler_stub

urlpatterns = [
    path('admin/', admin.site.urls)
]

TESTING = "test" in sys.argv or "PYTEST_VERSION" in os.environ

if not TESTING and settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns = [
        *urlpatterns,
    ] + debug_toolbar_urls()
