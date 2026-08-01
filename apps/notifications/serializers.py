from __future__ import annotations

from rest_framework import serializers

from apps.notifications.models import Notification


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
