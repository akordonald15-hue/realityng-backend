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


class ConversationThread(BaseModel):
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="conversation_threads",
    )
    inquiry = models.ForeignKey(
        "properties.Inquiry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversation_threads",
    )
    viewing = models.ForeignKey(
        "properties.Viewing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversation_threads",
    )
    application = models.ForeignKey(
        "properties.RentalApplication",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversation_threads",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_conversation_threads",
    )
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"ConversationThread<{self.id}>"


class ConversationParticipant(BaseModel):
    thread = models.ForeignKey(
        ConversationThread,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversation_participations",
    )
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["thread", "user"], name="unique_thread_participant"
            )
        ]
        indexes = [
            models.Index(fields=["user", "thread"]),
            models.Index(fields=["thread", "user"]),
        ]

    def __str__(self) -> str:
        return f"ConversationParticipant<{self.thread_id}:{self.user_id}>"


class Message(BaseModel):
    thread = models.ForeignKey(
        ConversationThread,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    body = models.TextField(max_length=4000)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["thread", "created_at"]),
            models.Index(fields=["thread", "sender", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Message<{self.id}>"
