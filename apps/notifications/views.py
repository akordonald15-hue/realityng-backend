from __future__ import annotations

from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.notifications.models import (
    ConversationParticipant,
    ConversationThread,
    Notification,
    NotificationPreference,
)
from apps.notifications.serializers import (
    ConversationThreadSerializer,
    MessageSerializer,
    NotificationPreferenceSerializer,
    NotificationSerializer,
)
from apps.notifications.services import (
    annotate_threads_with_unread_counts,
    create_message,
    mark_thread_read,
    unread_message_count_for_user,
)


class NotificationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope_by_action = {
        "mark_read": "notification_write",
        "mark_all_read": "notification_write",
    }

    def get_throttles(self):
        self.throttle_scope = self.throttle_scope_by_action.get(self.action)
        return super().get_throttles() if self.throttle_scope else []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = self.get_queryset().filter(read_at__isnull=True).count()
        return Response({"unread_count": count, "count": count})

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
        return Response({"marked_read": updated, "marked": updated})


class NotificationPreferenceViewSet(viewsets.GenericViewSet):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "notification_write"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return NotificationPreference.objects.none()
        return NotificationPreference.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get", "patch"], url_path="me")
    def me(self, request):
        preference, _ = NotificationPreference.objects.get_or_create(user=request.user)
        if request.method == "GET":
            return Response(self.get_serializer(preference).data)
        serializer = self.get_serializer(preference, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class ConversationThreadViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ConversationThreadSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope_by_action = {
        "create": "message_thread_create",
        "messages": "message_send",
    }

    def get_throttles(self):
        if self.action == "messages" and self.request.method == "GET":
            return []
        self.throttle_scope = self.throttle_scope_by_action.get(self.action)
        return super().get_throttles() if self.throttle_scope else []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ConversationThread.objects.none()
        return ConversationThread.objects.filter(
            participants__user=self.request.user
        ).select_related(
            "property",
            "inquiry",
            "viewing",
            "application",
            "created_by",
        ).prefetch_related(
            "participants",
            "participants__user",
        ).distinct()

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return annotate_threads_with_unread_counts(queryset, self.request.user).order_by(
            "-updated_at"
        )

    def perform_create(self, serializer) -> bool:
        existing_thread = self._existing_thread_for_context(serializer.validated_data)
        if existing_thread:
            serializer.instance = existing_thread
            return False
        thread = serializer.save(created_by=self.request.user)
        participant_ids = self._participant_ids_for_thread(thread)
        participant_ids.add(self.request.user.id)
        for user_id in participant_ids:
            ConversationParticipant.objects.get_or_create(
                thread=thread,
                user_id=user_id,
            )
        return True

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created = self.perform_create(serializer)
        status_code = 201 if created else 200
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status_code, headers=headers)

    def _existing_thread_for_context(self, data):
        queryset = ConversationThread.objects.filter(
            property=data.get("property"),
            inquiry=data.get("inquiry"),
            viewing=data.get("viewing"),
            application=data.get("application"),
        )
        return (
            queryset.filter(participants__user=self.request.user)
            .select_related("property", "inquiry", "viewing", "application", "created_by")
            .prefetch_related("participants", "participants__user")
            .first()
        )

    def _participant_ids_for_thread(self, thread) -> set:
        participant_ids = {thread.property.owner_id}
        if thread.inquiry_id:
            participant_ids.update(
                {thread.inquiry.interested_user_id, thread.inquiry.property_owner_id}
            )
        if thread.viewing_id:
            participant_ids.update({thread.viewing.requester_id, thread.viewing.property_owner_id})
        if thread.application_id:
            participant_ids.update(
                {thread.application.applicant_id, thread.application.property_owner_id}
            )
        return {user_id for user_id in participant_ids if user_id}

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, pk=None):
        thread = self.get_object()
        if request.method == "GET":
            queryset = thread.messages.select_related("sender").order_by(
                "thread_sequence",
                "created_at",
                "id",
            )
            after = request.query_params.get("after")
            if after:
                after_message = (
                    thread.messages.filter(id=after)
                    .only("id", "created_at", "thread_sequence")
                    .first()
                )
                if after_message:
                    if after_message.thread_sequence is not None:
                        queryset = queryset.filter(
                            thread_sequence__gt=after_message.thread_sequence
                        )
                    else:
                        queryset = queryset.filter(created_at__gt=after_message.created_at)
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = MessageSerializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = MessageSerializer(queryset, many=True)
            return Response(serializer.data)

        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = create_message(
            thread=thread,
            sender=request.user,
            body=serializer.validated_data["body"],
            client_message_id=serializer.validated_data.get("client_message_id"),
        )
        return Response(MessageSerializer(message).data, status=201)

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        thread = self.get_object()
        mark_thread_read(thread=thread, user=request.user)
        return Response({"marked_read": True})

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        count = unread_message_count_for_user(request.user)
        return Response({"unread_count": count, "count": count})
