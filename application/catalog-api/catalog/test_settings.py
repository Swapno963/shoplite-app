from catalog.settings import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

REDIS_URL = "redis://localhost:6379/15"
CHAOS_LATENCY_MS = 0
CHAOS_ERROR_RATE = 0.0
