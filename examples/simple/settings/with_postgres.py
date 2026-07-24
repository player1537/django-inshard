from .base import *  # noqa: F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'inshard_example',
        'USER': 'inshard',
        'PASSWORD': 'inshard',
        'HOST': 'localhost',
        'PORT': '5432',
    },
}
