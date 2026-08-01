from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel
from apps.notifications.choices import NotificationChannel, NotificationType


class Notification(BaseModel):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=40, choices=NotificationType.choices
    )
    channel = models.CharField(
        max_length=20,
        choices=NotificationChannel.choices,
        default=NotificationChannel.IN_APP,
    )
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    related_entity_type = models.CharField(max_length=100, blank=True)
    related_entity_id = models.UUIDField(null=True, blank=True)
    action_url = models.CharField(max_length=255, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "read_at"]),
            models.Index(fields=["recipient", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.notification_type} -> {self.recipient_id}"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

class NotificationPreference(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    in_app_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=True)
    lead_notifications = models.BooleanField(default=True)
    viewing_notifications = models.BooleanField(default=True)
    application_notifications = models.BooleanField(default=True)
    message_notifications = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"NotificationPreference<{self.user_id}>"

