"""App configuration for django-inshard."""

from django.apps import AppConfig


class DjangoInshardConfig(AppConfig):
    """App configuration for django-inshard."""

    name = "django_inshard"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self) -> None:
        from .lookups import register_lookups

        register_lookups()
