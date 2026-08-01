from __future__ import annotations

from rest_framework import serializers

from apps.notifications.models import (
    ConversationParticipant,
    ConversationThread,
    Message,
    Notification,
)


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "channel",
            "title",
            "body",
            "related_entity_type",
            "related_entity_id",
            "action_url",
            "read_at",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "thread", "sender", "body", "edited_at", "created_at"]
        read_only_fields = ["id", "thread", "sender", "edited_at", "created_at"]


class ConversationParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationParticipant
        fields = ["id", "user", "last_read_at"]
        read_only_fields = fields


class ConversationThreadSerializer(serializers.ModelSerializer):
    participants = ConversationParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ConversationThread
        fields = [
            "id",
            "property",
            "inquiry",
            "viewing",
            "application",
            "created_by",
            "is_closed",
            "participants",
            "last_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "participants",
            "last_message",
            "created_at",
            "updated_at",
        ]

    def get_last_message(self, obj) -> dict | None:
        message = obj.messages.order_by("-created_at").first()
        return MessageSerializer(message).data if message else None

