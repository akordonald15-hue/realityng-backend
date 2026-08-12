from __future__ import annotations

from celery import shared_task

from apps.notifications.services import send_notification_email_now


@shared_task(name="notifications.send_notification_email")
def send_notification_email(notification_id: str) -> bool:
    return send_notification_email_now(notification_id=notification_id)
