"""App configuration for django-inshard."""

from django.apps import AppConfig


class DjangoInshardConfig(AppConfig):
    """Registers the ``inshard`` lookup and the SQLite hash UDF."""

    name = 'django_inshard'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self) -> None:
        from django.db.backends.signals import connection_created

        from .lookups import register_lookups
        from .model_utils import _inshard_bucket

        def _on_connection(
            sender: type,  # noqa: ARG001
            connection: object,
            **kwargs: object,  # noqa: ARG001
        ) -> None:
            if connection.vendor == 'sqlite':  # type: ignore[union-attr]
                connection.connection.create_function(  # type: ignore[union-attr]
                    'inshard_bucket', 2, _inshard_bucket,
                )

        connection_created.connect(_on_connection)
        register_lookups()
