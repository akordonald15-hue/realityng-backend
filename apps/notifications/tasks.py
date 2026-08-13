from __future__ import annotations

from celery import shared_task

from apps.notifications.services import (
    process_due_realtime_outbox_events,
    process_realtime_outbox_event_now,
    send_notification_email_now,
)


@shared_task(
    bind=True,
    name="notifications.send_notification_email",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_notification_email(self, notification_id: str) -> bool:
    return send_notification_email_now(
        notification_id=notification_id,
        raise_on_failure=True,
    )


@shared_task(name="notifications.process_realtime_outbox_event")
def process_realtime_outbox_event(event_id: str) -> bool:
    return process_realtime_outbox_event_now(event_id=event_id)


@shared_task(name="notifications.process_due_realtime_outbox_events")
def process_due_realtime_outbox_events_task(limit: int = 100) -> int:
    return process_due_realtime_outbox_events(limit=limit)
