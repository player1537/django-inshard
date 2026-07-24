import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

SECRET_KEY = 'insecure-dev-key'

INSTALLED_APPS = [
    'django_inshard',
    'myapp',
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
