from __future__ import annotations

from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.notifications.models import (
    ConversationParticipant,
    ConversationThread,
    Notification,
)
from apps.notifications.serializers import (
    ConversationThreadSerializer,
    MessageSerializer,
    NotificationSerializer,
)


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = self.get_queryset().filter(read_at__isnull=True).count()
        return Response({"unread_count": count})

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at", "updated_at"])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(read_at__isnull=True).update(
            read_at=timezone.now()
        )
        return Response({"marked_read": updated})

class ConversationThreadViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ConversationThreadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ConversationThread.objects.none()
        return ConversationThread.objects.filter(
            participants__user=self.request.user
        ).distinct()

    def perform_create(self, serializer):
        thread = serializer.save(created_by=self.request.user)
        ConversationParticipant.objects.get_or_create(
            thread=thread, user=self.request.user
        )
        property_owner_id = (
            thread.property.owner_id
            if hasattr(thread.property, "owner_id")
            else None
        )
        if property_owner_id and property_owner_id != self.request.user.id:
            ConversationParticipant.objects.get_or_create(
                thread=thread, user_id=property_owner_id
            )

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, pk=None):
        thread = self.get_object()
        if request.method == "GET":
            queryset = thread.messages.all()
            serializer = MessageSerializer(queryset, many=True)
            return Response(serializer.data)

        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(thread=thread, sender=request.user)
        return Response(MessageSerializer(message).data, status=201)

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        thread = self.get_object()
        participant, _ = ConversationParticipant.objects.get_or_create(
            thread=thread, user=request.user
        )
        participant.last_read_at = timezone.now()
        participant.save(update_fields=["last_read_at", "updated_at"])
        return Response({"marked_read": True})

