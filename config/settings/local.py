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

