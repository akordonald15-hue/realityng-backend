"""Base Django settings for RealityNG."""

from __future__ import annotations

import logging.config
from datetime import timedelta
from pathlib import Path

import environ
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from apps.core.logging import LOGGING

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    DATABASE_URL=(str, "postgres://realityng:realityng@postgres:5432/realityng"),
    REDIS_URL=(str, "redis://redis:6379/0"),
    SENTRY_DSN=(str, ""),
    SENTRY_ENVIRONMENT=(str, "local"),
)

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY", default="change-me-in-local-development-secret-key")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
SITE_ID = 1

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "corsheaders",
    "django_celery_beat",
    "django_filters",
    "drf_spectacular",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
]

LOCAL_APPS = [
    "apps.common",
    "apps.core",
    "apps.accounts",
    "apps.properties",
    "apps.trust",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "apps.core.middleware.RequestCorrelationIdMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL"),
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.ActiveUserJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("DRF_THROTTLE_ANON_RATE", default="100/hour"),
        "user": env("DRF_THROTTLE_USER_RATE", default="1000/hour"),
        "auth_login": env("DRF_THROTTLE_AUTH_LOGIN_RATE", default="10/minute"),
        "auth_register": env("DRF_THROTTLE_AUTH_REGISTER_RATE", default="5/minute"),
        "auth_password_reset": env("DRF_THROTTLE_PASSWORD_RESET_RATE", default="5/minute"),
        "inquiry_create": env("DRF_THROTTLE_INQUIRY_CREATE_RATE", default="20/hour"),
        "viewing_create": env("DRF_THROTTLE_VIEWING_CREATE_RATE", default="20/hour"),
        "application_create": env("DRF_THROTTLE_APPLICATION_CREATE_RATE", default="10/hour"),
        "property_upload": env("DRF_THROTTLE_PROPERTY_UPLOAD_RATE", default="30/hour"),
    },
}

AUTH_USER_MODEL = "accounts.User"

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

LANDLORD_ROLE_AUTO_APPROVAL = env.bool("LANDLORD_ROLE_AUTO_APPROVAL", default=True)

SPECTACULAR_SETTINGS = {
    "TITLE": "RealityNG API",
    "DESCRIPTION": "API for RealityNG, a diaspora-focused Nigerian PropTech platform.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "ENUM_NAME_OVERRIDES": {
        "InquiryStatusEnum": "apps.properties.choices.InquiryStatus",
        "RentalApplicationStatusEnum": "apps.properties.choices.RentalApplicationStatus",
        "RoleEnum": "apps.accounts.choices.RoleName",
        "ViewingStatusEnum": "apps.properties.choices.ViewingStatus",
        "VerificationStatusEnum": "apps.trust.choices.VerificationStatus",
        "VerificationTypeEnum": "apps.trust.choices.VerificationType",
    },
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Lagos"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
USE_S3_MEDIA_STORAGE = env.bool("USE_S3_MEDIA_STORAGE", default=False)
PROPERTY_IMAGE_MAX_COUNT = env.int("PROPERTY_IMAGE_MAX_COUNT", default=30)
PROPERTY_IMAGE_MAX_SIZE_MB = env.int("PROPERTY_IMAGE_MAX_SIZE_MB", default=10)
PROPERTY_IMAGE_ALLOWED_TYPES = env.list(
    "PROPERTY_IMAGE_ALLOWED_TYPES",
    default=["image/jpeg", "image/png", "image/webp"],
)
PROPERTY_IMAGE_ALLOWED_EXTENSIONS = env.list(
    "PROPERTY_IMAGE_ALLOWED_EXTENSIONS",
    default=[".jpg", ".jpeg", ".png", ".webp"],
)

VERIFICATION_DOCUMENT_MAX_SIZE_MB = env.int("VERIFICATION_DOCUMENT_MAX_SIZE_MB", default=10)
VERIFICATION_DOCUMENT_ALLOWED_TYPES = env.list(
    "VERIFICATION_DOCUMENT_ALLOWED_TYPES",
    default=["application/pdf", "image/jpeg", "image/png"],
)
VERIFICATION_DOCUMENT_ALLOWED_EXTENSIONS = env.list(
    "VERIFICATION_DOCUMENT_ALLOWED_EXTENSIONS",
    default=[".pdf", ".jpg", ".jpeg", ".png"],
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=env("REDIS_URL"))
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=env("REDIS_URL"))
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

MINIO_ENDPOINT = env("MINIO_ENDPOINT", default="http://minio:9000")
MINIO_PUBLIC_ENDPOINT = env("MINIO_PUBLIC_ENDPOINT", default=MINIO_ENDPOINT)
MINIO_ACCESS_KEY = env("MINIO_ACCESS_KEY", default="minioadmin")
MINIO_SECRET_KEY = env("MINIO_SECRET_KEY", default="minioadmin")
MINIO_BUCKET_NAME = env("MINIO_BUCKET_NAME", default="realityng-local")

if USE_S3_MEDIA_STORAGE:
    AWS_ACCESS_KEY_ID = MINIO_ACCESS_KEY
    AWS_SECRET_ACCESS_KEY = MINIO_SECRET_KEY
    AWS_STORAGE_BUCKET_NAME = MINIO_BUCKET_NAME
    AWS_S3_ENDPOINT_URL = MINIO_ENDPOINT
    AWS_S3_REGION_NAME = env("MINIO_REGION_NAME", default="us-east-1")
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = env.bool("MINIO_QUERYSTRING_AUTH", default=False)
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

SENTRY_DSN = env("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        environment=env("SENTRY_ENVIRONMENT"),
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
        send_default_pii=False,
    )

LOGGING_CONFIG = None
logging.config.dictConfig(LOGGING)
