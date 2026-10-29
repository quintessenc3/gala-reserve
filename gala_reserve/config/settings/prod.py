from config.settings.base import *

DEBUG = False

ALLOWED_HOSTS = ['localhost']

REST_FRAMEWORK.update({
    'NUM_PROXIES': 1,
    #'DEFAULT_RENDERER_CLASSES': [
    #    'rest_framework.renderers.JSONRenderer'
    #]
})

USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True