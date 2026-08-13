"""Local development settings."""

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "backend"]
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
NOTIFICATION_EMAIL_TASKS_ENABLED = env.bool(  # noqa: F405
    "NOTIFICATION_EMAIL_TASKS_ENABLED",
    default=False,
)
REALTIME_OUTBOX_TASKS_ENABLED = env.bool(  # noqa: F405
    "REALTIME_OUTBOX_TASKS_ENABLED",
    default=False,
)

if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":  # noqa: F405
    CACHES = {  # noqa: F405
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "realityng-local",
        }
    }
