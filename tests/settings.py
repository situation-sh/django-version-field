# see https://docs.djangoproject.com/en/5.0/topics/testing/advanced/#id4
from pathlib import Path

from django.core.management.utils import get_random_secret_key

BASE_PATH = Path(__file__).parent.parent

DEBUG = True

SECRET_KEY = get_random_secret_key()

INSTALLED_APPS = [
    # for admin (see https://docs.djangoproject.com/en/5.0/ref/contrib/admin/#overview)
    "django.contrib.staticfiles",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "tests",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_PATH / "db.sqlite3",
    }
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    },
]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_PATH / "tests" / "static"

ROOT_URLCONF = "tests.urls"
