from __future__ import annotations

import json
import logging
import socket
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlparse
from uuid import UUID

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Count, F, Max, Model, Q
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.services import create_audit_log
from apps.notifications.choices import NotificationChannel, NotificationType
from apps.notifications.email import EmailMessage, get_email_provider
from apps.notifications.models import (
    ConversationParticipant,
    ConversationThread,
    Message,
    Notification,
    NotificationPreference,
    RealtimeOutboxEvent,
)
from apps.notifications.serializers import MessageSerializer, NotificationSerializer

logger = logging.getLogger(__name__)

MANDATORY_NOTIFICATION_TYPES = {NotificationType.SYSTEM}
EMAIL_NOTIFICATION_TYPES = {
    NotificationType.INQUIRY_CREATED,
    NotificationType.INQUIRY_STATUS_CHANGED,
    NotificationType.VIEWING_REQUESTED,
    NotificationType.VIEWING_CONFIRMED,
    NotificationType.VIEWING_RESCHEDULED,
    NotificationType.VIEWING_CANCELLED,
    NotificationType.APPLICATION_SUBMITTED,
    NotificationType.APPLICATION_STATUS_CHANGED,
    NotificationType.LEAD_ASSIGNED,
    NotificationType.LEAD_STAGE_CHANGED,
    NotificationType.FOLLOW_UP_DUE,
    NotificationType.NEW_MESSAGE,
}
OUTBOX_MAX_ATTEMPTS = 5
OUTBOX_RETRY_DELAYS_SECONDS = [0, 5, 15, 60, 300]


@dataclass(frozen=True)
class EmailDeliveryResult:
    queued: bool
    reason: str = ""


def notification_group_name(user_id) -> str:
    return f"realityng.notifications.user.{user_id}"


def thread_group_name(thread_id) -> str:
    return f"realityng.messages.thread.{thread_id}"


def create_notification(
    *,
    recipient,
    notification_type: str,
    title: str,
    body: str = "",
    related_entity: Model | None = None,
    action_url: str = "",
    channel: str = NotificationChannel.IN_APP,
    force: bool = False,
    send_email: bool = True,
) -> Notification | None:
    if recipient is None:
        return None
    if not should_notify(recipient, notification_type, channel, force=force):
        return None
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        channel=channel,
        title=title,
        body=body,
        related_entity_type=related_entity.__class__.__name__ if related_entity else "",
        related_entity_id=related_entity.id if related_entity else None,
        action_url=action_url,
    )
    enqueue_realtime_notification(notification)
    if send_email and notification_type in EMAIL_NOTIFICATION_TYPES:
        if should_notify(
            recipient,
            notification_type,
            NotificationChannel.EMAIL,
            force=force,
        ):
            transaction.on_commit(
                lambda: queue_transactional_email(notification_id=notification.id)
            )
    return notification


def should_notify(
    user,
    notification_type: str,
    channel: str = NotificationChannel.IN_APP,
    *,
    force: bool = False,
) -> bool:
    if force or notification_type in MANDATORY_NOTIFICATION_TYPES:
        return True
    preference, _ = NotificationPreference.objects.get_or_create(user=user)
    if channel == NotificationChannel.IN_APP and not preference.in_app_enabled:
        return False
    if channel == NotificationChannel.EMAIL and not preference.email_enabled:
        return False
    category_fields = {
        NotificationType.LEAD_ASSIGNED: "lead_notifications",
        NotificationType.LEAD_STAGE_CHANGED: "lead_notifications",
        NotificationType.FOLLOW_UP_DUE: "lead_notifications",
        NotificationType.VIEWING_REQUESTED: "viewing_notifications",
        NotificationType.VIEWING_CONFIRMED: "viewing_notifications",
        NotificationType.VIEWING_RESCHEDULED: "viewing_notifications",
        NotificationType.VIEWING_CANCELLED: "viewing_notifications",
        NotificationType.APPLICATION_SUBMITTED: "application_notifications",
        NotificationType.APPLICATION_STATUS_CHANGED: "application_notifications",
        NotificationType.NEW_MESSAGE: "message_notifications",
    }
    category_field = category_fields.get(notification_type)
    if category_field is None:
        return True
    return bool(getattr(preference, category_field, True))


def queue_transactional_email(*, notification_id) -> EmailDeliveryResult:
    if not getattr(settings, "NOTIFICATION_EMAIL_TASKS_ENABLED", False):
        return EmailDeliveryResult(queued=False, reason="disabled")
    if not _celery_broker_is_reachable():
        return EmailDeliveryResult(queued=False, reason="broker_unavailable")
    try:
        from apps.notifications.tasks import send_notification_email

        send_notification_email.apply_async(args=[str(notification_id)], retry=False)
        return EmailDeliveryResult(queued=True)
    except Exception as exc:  # pragma: no cover - depends on broker availability
        logger.warning(
            "notification_email_queue_failed",
            extra={"notification_id": str(notification_id), "error": exc.__class__.__name__},
        )
        return EmailDeliveryResult(queued=False, reason=exc.__class__.__name__)


def send_notification_email_now(*, notification_id, raise_on_failure: bool = False) -> bool:
    try:
        notification = Notification.objects.select_related("recipient").get(id=notification_id)
    except Notification.DoesNotExist:
        return False
    if not should_notify(
        notification.recipient,
        notification.notification_type,
        NotificationChannel.EMAIL,
    ):
        return False
    try:
        if not notification.recipient.email:
            return False
        return get_email_provider().send(
            EmailMessage(
                subject=notification.title,
                body=notification.body or notification.title,
                recipient=notification.recipient.email,
            )
        )
    except Exception as exc:
        logger.warning(
            "notification_email_send_failed",
            extra={"notification_id": str(notification.id), "error": exc.__class__.__name__},
        )
        if raise_on_failure:
            raise
        return False
    return True


def enqueue_realtime_notification(notification: Notification) -> RealtimeOutboxEvent:
    payload = {
        "notification_id": str(notification.id),
    }
    event, _ = RealtimeOutboxEvent.objects.get_or_create(
        event_type=RealtimeOutboxEvent.EventType.NOTIFICATION_CREATED,
        aggregate_id=notification.id,
        defaults={
            "aggregate_type": "Notification",
            "recipient_user": notification.recipient,
            "payload": payload,
        },
    )
    transaction.on_commit(lambda: queue_realtime_outbox_processing(event_id=event.id))
    return event


def enqueue_realtime_message(message: Message) -> RealtimeOutboxEvent:
    payload = {
        "message_id": str(message.id),
    }
    event, _ = RealtimeOutboxEvent.objects.get_or_create(
        event_type=RealtimeOutboxEvent.EventType.MESSAGE_CREATED,
        aggregate_id=message.id,
        defaults={
            "aggregate_type": "Message",
            "conversation_thread": message.thread,
            "payload": payload,
        },
    )
    transaction.on_commit(lambda: queue_realtime_outbox_processing(event_id=event.id))
    return event


def queue_realtime_outbox_processing(*, event_id) -> bool:
    if not getattr(settings, "REALTIME_OUTBOX_TASKS_ENABLED", False):
        return False
    if not _celery_broker_is_reachable():
        logger.warning(
            "realtime.outbox.queue_skipped",
            extra={"event_id": str(event_id), "reason": "broker_unavailable"},
        )
        return False
    try:
        from apps.notifications.tasks import process_realtime_outbox_event

        process_realtime_outbox_event.apply_async(args=[str(event_id)], retry=False)
        return True
    except Exception as exc:  # pragma: no cover - depends on broker availability
        logger.warning(
            "realtime.outbox.queue_failed",
            extra={"event_id": str(event_id), "error": exc.__class__.__name__},
        )
        return False


def broadcast_notification(notification_id) -> None:
    try:
        notification = Notification.objects.select_related("recipient").get(id=notification_id)
    except Notification.DoesNotExist:
        return
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    payload = _json_safe_payload(NotificationSerializer(notification).data)
    unread_count = Notification.objects.filter(
        recipient=notification.recipient,
        read_at__isnull=True,
    ).count()
    async_to_sync(channel_layer.group_send)(
        notification_group_name(notification.recipient_id),
        {
            "type": "notification.created",
            "notification": payload,
            "unread_count": unread_count,
        },
    )


def unread_message_count_for_user(user: User) -> int:
    return (
        Message.objects.filter(thread__participants__user=user)
        .exclude(sender=user)
        .filter(
            Q(thread__participants__user=user, thread__participants__last_read_at__isnull=True)
            | Q(
                thread__participants__user=user,
                created_at__gt=F("thread__participants__last_read_at"),
            )
        )
        .distinct()
        .count()
    )


def annotate_threads_with_unread_counts(queryset, user: User):
    return queryset.annotate(
        unread_count=Count(
            "messages",
            filter=(
                ~Q(messages__sender=user)
                & (
                    Q(participants__user=user, participants__last_read_at__isnull=True)
                    | Q(
                        participants__user=user,
                        messages__created_at__gt=F("participants__last_read_at"),
                    )
                )
            ),
            distinct=True,
        )
    )


def create_message(
    *,
    thread: ConversationThread,
    sender: User,
    body: str,
    client_message_id: UUID | str | None = None,
) -> Message:
    body = (body or "").strip()
    if not body:
        raise serializers.ValidationError({"body": "Message body is required."})
    max_length = Message._meta.get_field("body").max_length or 4000
    if len(body) > max_length:
        raise serializers.ValidationError(
            {"body": f"Message must be {max_length} characters or fewer."}
        )
    if thread.is_closed:
        raise serializers.ValidationError({"detail": "This conversation is closed."})
    if not ConversationParticipant.objects.filter(thread=thread, user=sender).exists():
        raise serializers.ValidationError({"detail": "You are not a participant in this thread."})
    parsed_client_message_id = _parse_client_message_id(client_message_id)
    if parsed_client_message_id:
        existing = Message.objects.filter(
            thread=thread,
            sender=sender,
            client_message_id=parsed_client_message_id,
        ).first()
        if existing:
            logger.info(
                "message.idempotency.hit",
                extra={
                    "thread_id": str(thread.id),
                    "sender_id": str(sender.id),
                    "message_id": str(existing.id),
                },
            )
            return existing

    with transaction.atomic():
        ConversationThread.objects.select_for_update().get(id=thread.id)
        next_sequence = (
            Message.objects.filter(thread=thread).aggregate(
                max_sequence=Max("thread_sequence")
            )["max_sequence"]
            or 0
        ) + 1
        message = Message.objects.create(
            thread=thread,
            sender=sender,
            body=body,
            client_message_id=parsed_client_message_id,
            thread_sequence=next_sequence,
        )
        thread.updated_at = timezone.now()
        thread.save(update_fields=["updated_at"])
        create_audit_log(
            actor=sender,
            action="message.sent",
            entity=message,
            metadata={"thread_id": str(thread.id)},
        )
        recipients = [
            participant.user
            for participant in thread.participants.select_related("user")
            if participant.user_id != sender.id
        ]
        for recipient in recipients:
            create_notification(
                recipient=recipient,
                notification_type=NotificationType.NEW_MESSAGE,
                title="New message",
                body=body[:200],
                related_entity=message,
                action_url=f"/dashboard/messages/{thread.id}",
            )
        enqueue_realtime_message(message)
    return message


def _parse_client_message_id(client_message_id: UUID | str | None) -> UUID | None:
    if not client_message_id:
        return None
    try:
        if isinstance(client_message_id, UUID):
            return client_message_id
        return UUID(str(client_message_id))
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError(
            {"client_message_id": "client_message_id must be a valid UUID."}
        ) from exc


def mark_thread_read(*, thread: ConversationThread, user: User) -> ConversationParticipant:
    try:
        participant = ConversationParticipant.objects.get(thread=thread, user=user)
    except ConversationParticipant.DoesNotExist as exc:
        raise serializers.ValidationError(
            {"detail": "You are not a participant in this thread."}
        ) from exc
    participant.last_read_at = timezone.now()
    participant.save(update_fields=["last_read_at", "updated_at"])
    create_audit_log(
        actor=user,
        action="message.read",
        entity=thread,
        metadata={"thread_id": str(thread.id)},
    )
    return participant


def broadcast_message(message_id) -> None:
    try:
        message = Message.objects.select_related("sender", "thread").get(id=message_id)
    except Message.DoesNotExist:
        return
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        thread_group_name(message.thread_id),
        {
            "type": "message.created",
            "message": _json_safe_payload(MessageSerializer(message).data),
        },
    )


def _json_safe_payload(payload):
    return json.loads(json.dumps(payload, cls=DjangoJSONEncoder))


def _celery_broker_is_reachable() -> bool:
    broker_url = getattr(settings, "CELERY_BROKER_URL", "")
    parsed = urlparse(broker_url)
    if parsed.scheme not in {"redis", "rediss"}:
        return True
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    timeout = float(getattr(settings, "CELERY_BROKER_CONNECTION_TIMEOUT", 2.0))
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def publish_realtime_outbox_event(event: RealtimeOutboxEvent) -> None:
    if event.event_type == RealtimeOutboxEvent.EventType.MESSAGE_CREATED:
        message_id = event.payload.get("message_id") or event.aggregate_id
        broadcast_message(message_id)
        return
    if event.event_type == RealtimeOutboxEvent.EventType.NOTIFICATION_CREATED:
        notification_id = event.payload.get("notification_id") or event.aggregate_id
        broadcast_notification(notification_id)
        return
    raise ValueError(f"Unsupported realtime outbox event type: {event.event_type}")


def process_realtime_outbox_event_now(*, event_id) -> bool:
    event = _claim_outbox_event(event_id=event_id)
    if event is None:
        return False
    try:
        publish_realtime_outbox_event(event)
    except Exception as exc:
        _record_outbox_failure(event=event, exc=exc)
        logger.warning(
            "realtime.broadcast.failed",
            extra={
                "event_id": str(event.id),
                "event_type": event.event_type,
                "attempt_count": event.attempt_count,
                "error": exc.__class__.__name__,
            },
        )
        return False
    event.status = RealtimeOutboxEvent.Status.DELIVERED
    event.processed_at = timezone.now()
    event.last_error = ""
    event.save(update_fields=["status", "processed_at", "last_error", "updated_at"])
    return True


def process_due_realtime_outbox_events(*, limit: int = 100) -> int:
    now = timezone.now()
    processed = 0
    due_ids = list(
        RealtimeOutboxEvent.objects.filter(
            status__in=[
                RealtimeOutboxEvent.Status.PENDING,
                RealtimeOutboxEvent.Status.FAILED,
            ],
        )
        .filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now))
        .order_by("created_at", "id")
        .values_list("id", flat=True)[:limit]
    )
    for event_id in due_ids:
        if process_realtime_outbox_event_now(event_id=event_id):
            processed += 1
    return processed


def _claim_outbox_event(*, event_id) -> RealtimeOutboxEvent | None:
    with transaction.atomic():
        queryset = RealtimeOutboxEvent.objects.select_for_update()
        try:
            event = queryset.get(id=event_id)
        except RealtimeOutboxEvent.DoesNotExist:
            return None
        if event.status in [
            RealtimeOutboxEvent.Status.DELIVERED,
            RealtimeOutboxEvent.Status.DEAD,
            RealtimeOutboxEvent.Status.PROCESSING,
        ]:
            return None
        if event.next_attempt_at and event.next_attempt_at > timezone.now():
            return None
        event.status = RealtimeOutboxEvent.Status.PROCESSING
        event.attempt_count += 1
        event.save(update_fields=["status", "attempt_count", "updated_at"])
        return event


def _record_outbox_failure(*, event: RealtimeOutboxEvent, exc: Exception) -> None:
    event.last_error = exc.__class__.__name__[:255]
    if event.attempt_count >= OUTBOX_MAX_ATTEMPTS:
        event.status = RealtimeOutboxEvent.Status.DEAD
        event.next_attempt_at = None
        logger.error(
            "realtime.outbox.dead",
            extra={"event_id": str(event.id), "event_type": event.event_type},
        )
    else:
        event.status = RealtimeOutboxEvent.Status.FAILED
        delay_index = min(event.attempt_count, len(OUTBOX_RETRY_DELAYS_SECONDS) - 1)
        event.next_attempt_at = timezone.now() + timedelta(
            seconds=OUTBOX_RETRY_DELAYS_SECONDS[delay_index]
        )
        logger.info(
            "realtime.broadcast.retried",
            extra={
                "event_id": str(event.id),
                "event_type": event.event_type,
                "next_attempt_at": event.next_attempt_at.isoformat(),
            },
        )
    event.save(update_fields=["status", "next_attempt_at", "last_error", "updated_at"])
