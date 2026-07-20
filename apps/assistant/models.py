from django.conf import settings
from django.db import models

from apps.common.models import BaseModel


class AIConversation(BaseModel):
    """A persisted AI assistant conversation for a single user session thread."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"
        ARCHIVED = "archived", "Archived"

    class Provider(models.TextChoices):
        ANTHROPIC = "anthropic", "Anthropic"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    provider = models.CharField(
        max_length=30,
        choices=Provider.choices,
        default=Provider.ANTHROPIC,
    )
    title = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self) -> str:
        return f"AIConversation({self.id}, user={self.user_id}, status={self.status})"


class AIMessage(BaseModel):
    """A single turn within an AIConversation."""

    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"
        TOOL = "tool", "Tool"

    conversation = models.ForeignKey(
        AIConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    content = models.TextField(blank=True, default="")
    tool_calls = models.JSONField(default=list, blank=True)
    tool_results = models.JSONField(default=list, blank=True)
    token_count = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"AIMessage({self.id}, conversation={self.conversation_id}, role={self.role})"
