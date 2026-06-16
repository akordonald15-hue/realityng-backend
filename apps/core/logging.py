"""Structured logging configuration."""

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
        },
        "console": {
            "format": "%(levelname)s %(asctime)s %(name)s [%(request_id)s] %(message)s",
        },
    },
    "filters": {
        "request_id": {
            "()": "apps.core.middleware.RequestIdLogFilter",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["request_id"],
        }
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        }
    },
}

