from __future__ import annotations

import logging
from dataclasses import dataclass

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.db import transaction
from django.db.models import Count, F, Model, Q
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
    transaction.on_commit(lambda: broadcast_notification(notification.id))
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
    try:
        from apps.notifications.tasks import send_notification_email

        send_notification_email.delay(str(notification_id))
        return EmailDeliveryResult(queued=True)
    except Exception as exc:  # pragma: no cover - depends on broker availability
        logger.warning(
            "notification_email_queue_failed",
            extra={"notification_id": str(notification_id), "error": exc.__class__.__name__},
        )
        return EmailDeliveryResult(queued=False, reason=exc.__class__.__name__)


def send_notification_email_now(*, notification_id) -> bool:
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
        return False
    return True


def broadcast_notification(notification_id) -> None:
    try:
        notification = Notification.objects.select_related("recipient").get(id=notification_id)
    except Notification.DoesNotExist:
        return
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    payload = NotificationSerializer(notification).data
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

    with transaction.atomic():
        message = Message.objects.create(thread=thread, sender=sender, body=body)
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
        transaction.on_commit(lambda: broadcast_message(message.id))
    return message


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
            "message": MessageSerializer(message).data,
        },
    )
