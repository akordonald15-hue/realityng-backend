from __future__ import annotations

from rest_framework import serializers

from apps.accounts.services import user_is_admin
from apps.notifications.models import (
    ConversationParticipant,
    ConversationThread,
    Message,
    Notification,
    NotificationPreference,
)
from apps.properties.choices import PropertyStatus


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


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "in_app_enabled",
            "email_enabled",
            "lead_notifications",
            "viewing_notifications",
            "application_notifications",
            "message_notifications",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            "id",
            "thread",
            "sender",
            "body",
            "client_message_id",
            "thread_sequence",
            "edited_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "thread",
            "sender",
            "thread_sequence",
            "edited_at",
            "created_at",
        ]


class ConversationParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationParticipant
        fields = ["id", "user", "last_read_at"]
        read_only_fields = fields


class ConversationThreadSerializer(serializers.ModelSerializer):
    participants = ConversationParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True, default=0)

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
            "unread_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "participants",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]

    def get_last_message(self, obj) -> dict | None:
        message = obj.messages.order_by("-created_at").first()
        return MessageSerializer(message).data if message else None

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        prop = attrs.get("property")
        inquiry = attrs.get("inquiry")
        viewing = attrs.get("viewing")
        application = attrs.get("application")

        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authentication is required.")

        if prop and prop.status != PropertyStatus.APPROVED and not (
            user_is_admin(user) or prop.owner_id == user.id
        ):
            raise serializers.ValidationError(
                {"property": "Conversations can only be started for available properties."}
            )

        linked_objects = [obj for obj in (inquiry, viewing, application) if obj is not None]
        for linked in linked_objects:
            if linked.property_id != prop.id:
                raise serializers.ValidationError(
                    "Linked inquiry, viewing, or application must belong to the property."
                )

        if inquiry and user.id not in {inquiry.interested_user_id, inquiry.property_owner_id}:
            raise serializers.ValidationError(
                {"inquiry": "You are not authorized for this inquiry conversation."}
            )
        if viewing and user.id not in {viewing.requester_id, viewing.property_owner_id}:
            raise serializers.ValidationError(
                {"viewing": "You are not authorized for this viewing conversation."}
            )
        if application and user.id not in {
            application.applicant_id,
            application.property_owner_id,
        }:
            raise serializers.ValidationError(
                {"application": "You are not authorized for this application conversation."}
            )

        if not linked_objects:
            raise serializers.ValidationError(
                {"property": "Start conversations from an inquiry, viewing, or application."}
            )

        return attrs
