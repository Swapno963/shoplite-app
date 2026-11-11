import os
from pathlib import Path

from catalog.logging_config import JsonFormatter

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "*").split(",")
    if host.strip()
]

SERVICE_NAME = os.getenv("SERVICE_NAME", "catalog-api")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ORDERS_QUEUE = os.getenv("ORDERS_QUEUE", "orders:pending")

CHAOS_LATENCY_MS = int(os.getenv("CHAOS_LATENCY_MS", "0") or "0")
CHAOS_ERROR_RATE = float(os.getenv("CHAOS_ERROR_RATE", "0") or "0")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "api",
]

MIDDLEWARE = [
    "api.middleware.TraceIdMiddleware",
    "api.middleware.MetricsMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.security.SecurityMiddleware",
]

ROOT_URLCONF = "catalog.urls"
WSGI_APPLICATION = "catalog.wsgi.application"
APPEND_SLASH = False

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("POSTGRES_DB", "shoplite"),
        "USER": os.getenv("POSTGRES_USER", "shoplite"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "shoplite"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "UNAUTHENTICATED_USER": None,
}

CORS_ALLOW_ALL_ORIGINS = os.getenv("CORS_ALLOW_ALL_ORIGINS", "true").lower() in (
    "1",
    "true",
    "yes",
)
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": JsonFormatter,
        }
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        }
    },
    "root": {
        "handlers": ["stdout"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
}
