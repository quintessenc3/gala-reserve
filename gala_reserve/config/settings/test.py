import factory

from config.settings.base import *

DEBUG = False

factory.Faker.override_default_locale('ru_RU')

CELERY_TASK_ALWAYS_EAGER = True

STORAGES.update({
    'default': {
        "BACKEND": "django.core.files.storage.InMemoryStorage"
    }
})

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']