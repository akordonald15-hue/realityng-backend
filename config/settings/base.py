"""Base Django settings for RealityNG."""

from __future__ import annotations

import logging.config
from datetime import timedelta
from pathlib import Path

import environ
import sentry_sdk
from corsheaders.defaults import default_headers
from sentry_sdk.integrations.django import DjangoIntegration

from apps.core.logging import LOGGING

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CORS_ALLOWED_ORIGINS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    CORS_ALLOW_CREDENTIALS=(bool, True),
    DATABASE_URL=(str, "postgres://realityng:realityng@postgres:5432/realityng"),
    REDIS_URL=(str, "redis://redis:6379/0"),
    SENTRY_DSN=(str, ""),
    SENTRY_ENVIRONMENT=(str, "local"),
)

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)

SECRET_KEY = env("SECRET_KEY", default="change-me-in-local-development-secret-key")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
ANTHROPIC_MODEL = env("ANTHROPIC_MODEL", default="claude-sonnet-5")
AI_ASSISTANT_ENABLED = env.bool("AI_ASSISTANT_ENABLED", default=True)
AI_PROVIDER_MODE = env("AI_PROVIDER_MODE", default="anthropic").strip().lower()
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
    "apps.assistant",
    "apps.services",
    "apps.inspections",
    "apps.construction",
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
        "service_portfolio_upload": env(
            "DRF_THROTTLE_SERVICE_PORTFOLIO_UPLOAD_RATE",
            default="30/hour",
        ),
        "service_quote_request_create": env(
            "DRF_THROTTLE_SERVICE_QUOTE_REQUEST_CREATE_RATE",
            default="10/hour",
        ),
        "service_quote_request_manage": env(
            "DRF_THROTTLE_SERVICE_QUOTE_REQUEST_MANAGE_RATE",
            default="120/hour",
        ),
        "service_review_create": env("DRF_THROTTLE_SERVICE_REVIEW_CREATE_RATE", default="5/hour"),
        "service_review_update": env("DRF_THROTTLE_SERVICE_REVIEW_UPDATE_RATE", default="20/hour"),
        "service_review_response": env(
            "DRF_THROTTLE_SERVICE_REVIEW_RESPONSE_RATE",
            default="20/hour",
        ),
        "service_review_flag": env("DRF_THROTTLE_SERVICE_REVIEW_FLAG_RATE", default="20/hour"),
        "service_complaint_create": env(
            "DRF_THROTTLE_SERVICE_COMPLAINT_CREATE_RATE",
            default="10/hour",
        ),
        "service_provider_appeal_create": env(
            "DRF_THROTTLE_SERVICE_PROVIDER_APPEAL_CREATE_RATE",
            default="5/hour",
        ),
        "inspection_request_create": env(
            "DRF_THROTTLE_INSPECTION_REQUEST_CREATE_RATE",
            default="10/hour",
        ),
        "inspection_request_transition": env(
            "DRF_THROTTLE_INSPECTION_REQUEST_TRANSITION_RATE",
            default="60/hour",
        ),
        "inspection_schedule": env("DRF_THROTTLE_INSPECTION_SCHEDULE_RATE", default="30/hour"),
        "walkthrough_upload": env("DRF_THROTTLE_WALKTHROUGH_UPLOAD_RATE", default="20/hour"),
        "walkthrough_submit": env("DRF_THROTTLE_WALKTHROUGH_SUBMIT_RATE", default="40/hour"),
        "inspection_report_submit": env(
            "DRF_THROTTLE_INSPECTION_REPORT_SUBMIT_RATE",
            default="30/hour",
        ),
        "inspection_evidence_upload": env(
            "DRF_THROTTLE_INSPECTION_EVIDENCE_UPLOAD_RATE",
            default="40/hour",
        ),
        "inspection_signed_url": env(
            "DRF_THROTTLE_INSPECTION_SIGNED_URL_RATE",
            default="120/hour",
        ),
        "construction_project_create": env(
            "DRF_THROTTLE_CONSTRUCTION_PROJECT_CREATE_RATE",
            default="20/hour",
        ),
        "construction_evidence_upload": env(
            "DRF_THROTTLE_CONSTRUCTION_EVIDENCE_UPLOAD_RATE",
            default="40/hour",
        ),
        "construction_signed_url": env(
            "DRF_THROTTLE_CONSTRUCTION_SIGNED_URL_RATE",
            default="120/hour",
        ),
        "ai_assistant_message": env("DRF_THROTTLE_AI_ASSISTANT_MESSAGE_RATE", default="20/hour"),
    },
}

AUTH_USER_MODEL = "accounts.User"
SERVICE_REVIEW_EDIT_WINDOW_HOURS = env.int("SERVICE_REVIEW_EDIT_WINDOW_HOURS", default=48)

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
        "AIConversationStatusEnum": "apps.assistant.models.AIConversation.Status",
        "AIConversationProviderEnum": "apps.assistant.models.AIConversation.Provider",
        "InquiryStatusEnum": "apps.properties.choices.InquiryStatus",
        "RentalApplicationStatusEnum": "apps.properties.choices.RentalApplicationStatus",
        "RoleEnum": "apps.accounts.choices.RoleName",
        "ViewingStatusEnum": "apps.properties.choices.ViewingStatus",
        "VerificationStatusEnum": "apps.trust.choices.VerificationStatus",
        "VerificationTypeEnum": "apps.trust.choices.VerificationType",
        "InspectionRequestStatusEnum": "apps.inspections.choices.InspectionRequestStatus",
        "WalkthroughStatusEnum": "apps.inspections.choices.WalkthroughStatus",
        "InspectionReportStatusEnum": "apps.inspections.choices.InspectionReportStatus",
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
SERVICE_PORTFOLIO_IMAGE_MAX_COUNT = env.int("SERVICE_PORTFOLIO_IMAGE_MAX_COUNT", default=20)
SERVICE_PORTFOLIO_IMAGE_MAX_SIZE_MB = env.int("SERVICE_PORTFOLIO_IMAGE_MAX_SIZE_MB", default=10)
SERVICE_PORTFOLIO_IMAGE_ALLOWED_TYPES = env.list(
    "SERVICE_PORTFOLIO_IMAGE_ALLOWED_TYPES",
    default=PROPERTY_IMAGE_ALLOWED_TYPES,
)
SERVICE_PORTFOLIO_IMAGE_ALLOWED_EXTENSIONS = env.list(
    "SERVICE_PORTFOLIO_IMAGE_ALLOWED_EXTENSIONS",
    default=PROPERTY_IMAGE_ALLOWED_EXTENSIONS,
)
SERVICE_COMPLAINT_EVIDENCE_MAX_SIZE_MB = env.int(
    "SERVICE_COMPLAINT_EVIDENCE_MAX_SIZE_MB",
    default=10,
)
SERVICE_COMPLAINT_EVIDENCE_ALLOWED_TYPES = env.list(
    "SERVICE_COMPLAINT_EVIDENCE_ALLOWED_TYPES",
    default=["application/pdf", "image/jpeg", "image/png"],
)
SERVICE_COMPLAINT_EVIDENCE_ALLOWED_EXTENSIONS = env.list(
    "SERVICE_COMPLAINT_EVIDENCE_ALLOWED_EXTENSIONS",
    default=[".pdf", ".jpg", ".jpeg", ".png"],
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
VERIFICATION_DOCUMENT_BUCKET_NAME = env(
    "VERIFICATION_DOCUMENT_BUCKET_NAME",
    default="realityng-verification-private",
)
VERIFICATION_SIGNED_URL_EXPIRY = env.int("VERIFICATION_SIGNED_URL_EXPIRY", default=300)

WALKTHROUGH_MAX_FILE_SIZE_MB = env.int("WALKTHROUGH_MAX_FILE_SIZE_MB", default=100)
WALKTHROUGH_MAX_VIDEOS_PER_PROPERTY = env.int("WALKTHROUGH_MAX_VIDEOS_PER_PROPERTY", default=3)
WALKTHROUGH_ALLOWED_MIME_TYPES = env.list(
    "WALKTHROUGH_ALLOWED_MIME_TYPES",
    default=["video/mp4", "video/webm"],
)
WALKTHROUGH_ALLOWED_EXTENSIONS = env.list(
    "WALKTHROUGH_ALLOWED_EXTENSIONS",
    default=[".mp4", ".webm"],
)
WALKTHROUGH_STORAGE_BUCKET = env(
    "WALKTHROUGH_STORAGE_BUCKET",
    default="realityng-walkthroughs",
)
WALKTHROUGH_UPLOAD_URL_EXPIRY_SECONDS = env.int(
    "WALKTHROUGH_UPLOAD_URL_EXPIRY_SECONDS",
    default=900,
)
WALKTHROUGH_PUBLIC_BASE_URL = env("WALKTHROUGH_PUBLIC_BASE_URL", default="")
WALKTHROUGH_REQUIRE_MODERATION = env.bool("WALKTHROUGH_REQUIRE_MODERATION", default=True)

INSPECTION_EVIDENCE_BUCKET = env(
    "INSPECTION_EVIDENCE_BUCKET",
    default="realityng-inspection-evidence",
)
INSPECTION_REPORT_BUCKET = env(
    "INSPECTION_REPORT_BUCKET",
    default="realityng-inspection-reports",
)
INSPECTION_SIGNED_URL_EXPIRY_SECONDS = env.int(
    "INSPECTION_SIGNED_URL_EXPIRY_SECONDS",
    default=300,
)
INSPECTION_MAX_EVIDENCE_FILE_SIZE_MB = env.int(
    "INSPECTION_MAX_EVIDENCE_FILE_SIZE_MB",
    default=25,
)
INSPECTION_MAX_REPORT_FILE_SIZE_MB = env.int(
    "INSPECTION_MAX_REPORT_FILE_SIZE_MB",
    default=25,
)
INSPECTION_EVIDENCE_ALLOWED_MIME_TYPES = env.list(
    "INSPECTION_EVIDENCE_ALLOWED_MIME_TYPES",
    default=[
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
        "video/mp4",
        "video/webm",
        "audio/mpeg",
        "audio/wav",
    ],
)
INSPECTION_EVIDENCE_ALLOWED_EXTENSIONS = env.list(
    "INSPECTION_EVIDENCE_ALLOWED_EXTENSIONS",
    default=[".jpg", ".jpeg", ".png", ".webp", ".pdf", ".mp4", ".webm", ".mp3", ".wav"],
)
INSPECTION_REPORT_ALLOWED_MIME_TYPES = env.list(
    "INSPECTION_REPORT_ALLOWED_MIME_TYPES",
    default=["application/pdf", "image/jpeg", "image/png"],
)
INSPECTION_REPORT_ALLOWED_EXTENSIONS = env.list(
    "INSPECTION_REPORT_ALLOWED_EXTENSIONS",
    default=[".pdf", ".jpg", ".jpeg", ".png"],
)

CONSTRUCTION_EVIDENCE_BUCKET = env(
    "CONSTRUCTION_EVIDENCE_BUCKET",
    default="realityng-construction-evidence",
)
CONSTRUCTION_SIGNED_URL_EXPIRY_SECONDS = env.int(
    "CONSTRUCTION_SIGNED_URL_EXPIRY_SECONDS",
    default=300,
)
CONSTRUCTION_MAX_IMAGE_SIZE_MB = env.int("CONSTRUCTION_MAX_IMAGE_SIZE_MB", default=25)
CONSTRUCTION_MAX_VIDEO_SIZE_MB = env.int("CONSTRUCTION_MAX_VIDEO_SIZE_MB", default=100)
CONSTRUCTION_MAX_DOCUMENT_SIZE_MB = env.int("CONSTRUCTION_MAX_DOCUMENT_SIZE_MB", default=25)
CONSTRUCTION_ALLOWED_IMAGE_TYPES = env.list(
    "CONSTRUCTION_ALLOWED_IMAGE_TYPES",
    default=["image/jpeg", "image/png", "image/webp"],
)
CONSTRUCTION_ALLOWED_VIDEO_TYPES = env.list(
    "CONSTRUCTION_ALLOWED_VIDEO_TYPES",
    default=["video/mp4", "video/webm"],
)
CONSTRUCTION_ALLOWED_DOCUMENT_TYPES = env.list(
    "CONSTRUCTION_ALLOWED_DOCUMENT_TYPES",
    default=["application/pdf"],
)
CONSTRUCTION_ALLOWED_EXTENSIONS = env.list(
    "CONSTRUCTION_ALLOWED_EXTENSIONS",
    default=[".jpg", ".jpeg", ".png", ".webp", ".mp4", ".webm", ".pdf"],
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
CORS_ALLOW_CREDENTIALS = env("CORS_ALLOW_CREDENTIALS")
CORS_ALLOW_HEADERS = (*default_headers, "x-request-id", "sentry-trace", "baggage")

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
