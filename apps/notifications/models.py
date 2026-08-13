from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q

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
    client_message_id = models.UUIDField(null=True, blank=True)
    thread_sequence = models.PositiveIntegerField(null=True, blank=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["thread", "created_at"]),
            models.Index(fields=["thread", "created_at", "id"]),
            models.Index(fields=["thread", "thread_sequence"]),
            models.Index(fields=["thread", "sender", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["thread", "sender", "client_message_id"],
                condition=Q(client_message_id__isnull=False),
                name="unique_message_client_id_per_sender_thread",
            ),
            models.UniqueConstraint(
                fields=["thread", "thread_sequence"],
                condition=Q(thread_sequence__isnull=False),
                name="unique_message_sequence_per_thread",
            ),
        ]

    def __str__(self) -> str:
        return f"Message<{self.id}>"


class RealtimeOutboxEvent(BaseModel):
    class EventType(models.TextChoices):
        MESSAGE_CREATED = "message.created", "Message Created"
        NOTIFICATION_CREATED = "notification.created", "Notification Created"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"
        DEAD = "dead", "Dead"

    event_type = models.CharField(max_length=80, choices=EventType.choices)
    aggregate_type = models.CharField(max_length=80)
    aggregate_id = models.UUIDField()
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="realtime_outbox_events",
    )
    conversation_thread = models.ForeignKey(
        ConversationThread,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="realtime_outbox_events",
    )
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=255, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["status", "next_attempt_at", "created_at"]),
            models.Index(fields=["event_type", "aggregate_id"]),
            models.Index(fields=["recipient_user", "status"]),
            models.Index(fields=["conversation_thread", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["event_type", "aggregate_id"],
                name="unique_realtime_outbox_event_per_aggregate",
            )
        ]

    def __str__(self) -> str:
        return f"RealtimeOutboxEvent<{self.event_type}:{self.aggregate_id}>"
