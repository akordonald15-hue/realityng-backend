from rest_framework import serializers

from apps.assistant.models import AIConversation, AIMessage


class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = [
            "id",
            "role",
            "content",
            "tool_calls",
            "tool_results",
            "token_count",
            "created_at",
        ]
        read_only_fields = fields


class AIConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIConversation
        fields = [
            "id",
            "status",
            "provider",
            "title",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "provider", "created_at", "updated_at"]


class AIConversationDetailSerializer(AIConversationSerializer):
    messages = AIMessageSerializer(many=True, read_only=True)

    class Meta(AIConversationSerializer.Meta):
        fields = AIConversationSerializer.Meta.fields + ["messages"]


class SendMessageSerializer(serializers.Serializer):
    content = serializers.CharField(allow_blank=False, trim_whitespace=True, max_length=8000)
