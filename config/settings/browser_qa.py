"""Isolated local settings for the real-browser Sprint 15 QA gate."""

from .local import *  # noqa: F403

REST_FRAMEWORK = {  # noqa: F405
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_THROTTLE_RATES": {
        **REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],  # noqa: F405
        "anon": "10000/hour",
        "user": "10000/hour",
        "auth_login": "10000/hour",
    },
}

CELERY_TASK_ALWAYS_EAGER = True
REALTIME_OUTBOX_TASKS_ENABLED = True
