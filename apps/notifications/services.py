from __future__ import annotations

from django.db.models import Model

from apps.notifications.choices import NotificationChannel
from apps.notifications.models import Notification


def create_notification(
    *,
    recipient,
    notification_type: str,
    title: str,
    body: str = "",
    related_entity: Model | None = None,
    action_url: str = "",
    channel: str = NotificationChannel.IN_APP,
) -> Notification | None:
    if recipient is None:
        return None
    return Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        channel=channel,
        title=title,
        body=body,
        related_entity_type=related_entity.__class__.__name__ if related_entity else "",
        related_entity_id=related_entity.id if related_entity else None,
        action_url=action_url,
    )
