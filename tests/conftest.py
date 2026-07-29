import django
from django.conf import settings


def pytest_configure() -> None:
    settings.configure(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "test_inshard",
                "USER": "inshard",
                "PASSWORD": "inshard",
                "HOST": "localhost",
                "PORT": "5432",
            },
        },
        INSTALLED_APPS=["django_inshard", "tests"],
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        MIGRATION_MODULES={"tests": None},
    )
    django.setup()
