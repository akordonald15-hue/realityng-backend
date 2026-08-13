from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog, User
from apps.notifications.choices import NotificationType
from apps.notifications.models import (
    ConversationParticipant,
    ConversationThread,
    Message,
    Notification,
    NotificationPreference,
    RealtimeOutboxEvent,
)
from apps.properties.choices import InquiryType, ListingType, PropertyStatus, PropertyType
from apps.properties.models import Inquiry, Property


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def owner(db):
    return User.objects.create_user(email="notify-owner@example.com", password="Pass12345!")


@pytest.fixture
def buyer(db):
    return User.objects.create_user(email="notify-buyer@example.com", password="Pass12345!")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="notify-other@example.com", password="Pass12345!")


@pytest.fixture
def property_listing(owner):
    return Property.objects.create(
        owner=owner,
        title="Approved Lekki Terrace",
        description="A verified terrace with easy access.",
        property_type=PropertyType.HOUSE,
        listing_type=ListingType.RENT,
        price=Decimal("2500000.00"),
        currency="NGN",
        country="Nigeria",
        state="Lagos",
        city="Lekki",
        address="Admiralty Way",
        bedrooms=3,
        bathrooms=3,
        parking_spaces=2,
        floor_area=Decimal("180.00"),
        status=PropertyStatus.APPROVED,
    )


@pytest.fixture
def inquiry(property_listing, buyer):
    return Inquiry.objects.create(
        property=property_listing,
        interested_user=buyer,
        property_owner=property_listing.owner,
        inquiry_type=InquiryType.RENT,
        message="I would like to inspect this home.",
    )


@pytest.mark.django_db
def test_user_lists_and_marks_only_own_notifications(api_client, owner, buyer):
    own_notification = Notification.objects.create(
        recipient=owner,
        notification_type=NotificationType.SYSTEM,
        title="Owner update",
    )
    other_notification = Notification.objects.create(
        recipient=buyer,
        notification_type=NotificationType.SYSTEM,
        title="Buyer update",
    )

    api_client.force_authenticate(owner)
    list_response = api_client.get(reverse("notifications-list"))
    assert list_response.status_code == 200
    assert [item["id"] for item in list_response.data["results"]] == [
        str(own_notification.id)
    ]

    denied = api_client.post(reverse("notifications-mark-read", args=[other_notification.id]))
    assert denied.status_code == 404

    marked = api_client.post(reverse("notifications-mark-read", args=[own_notification.id]))
    assert marked.status_code == 200
    assert marked.data["is_read"] is True

    count = api_client.get(reverse("notifications-unread-count"))
    assert count.status_code == 200
    assert count.data["unread_count"] == 0
    assert count.data["count"] == 0


@pytest.mark.django_db
def test_notification_preferences_are_current_user_scoped(api_client, owner, buyer):
    NotificationPreference.objects.create(user=buyer, email_enabled=False)

    api_client.force_authenticate(owner)
    response = api_client.patch(
        reverse("notification-preferences-me"),
        {"email_enabled": False, "lead_notifications": False},
        format="json",
    )

    assert response.status_code == 200
    owner_preference = NotificationPreference.objects.get(user=owner)
    buyer_preference = NotificationPreference.objects.get(user=buyer)
    assert owner_preference.email_enabled is False
    assert owner_preference.lead_notifications is False
    assert buyer_preference.email_enabled is False
    assert buyer_preference.lead_notifications is True


@pytest.mark.django_db
def test_inquiry_participant_can_create_thread_and_send_message(api_client, owner, buyer, inquiry):
    api_client.force_authenticate(buyer)

    create_response = api_client.post(
        reverse("conversation-threads-list"),
        {"property": str(inquiry.property_id), "inquiry": str(inquiry.id)},
        format="json",
    )

    assert create_response.status_code == 201
    thread = ConversationThread.objects.get(id=create_response.data["id"])
    assert set(thread.participants.values_list("user_id", flat=True)) == {owner.id, buyer.id}

    message_response = api_client.post(
        reverse("conversation-threads-messages", args=[thread.id]),
        {"body": "Please share available viewing slots.", "sender": str(owner.id)},
        format="json",
    )
    assert message_response.status_code == 201
    message = Message.objects.get(id=message_response.data["id"])
    assert message.sender_id == buyer.id
    assert Notification.objects.filter(
        recipient=owner,
        notification_type=NotificationType.NEW_MESSAGE,
        related_entity_id=message.id,
    ).exists()
    assert RealtimeOutboxEvent.objects.filter(
        event_type=RealtimeOutboxEvent.EventType.MESSAGE_CREATED,
        aggregate_id=message.id,
    ).exists()


@pytest.mark.django_db
def test_non_participant_cannot_access_or_post_to_thread(
    api_client,
    owner,
    buyer,
    other_user,
    inquiry,
):
    thread = ConversationThread.objects.create(
        property=inquiry.property,
        inquiry=inquiry,
        created_by=buyer,
    )
    ConversationParticipant.objects.create(thread=thread, user=buyer)
    ConversationParticipant.objects.create(thread=thread, user=owner)

    api_client.force_authenticate(other_user)
    detail_response = api_client.get(reverse("conversation-threads-detail", args=[thread.id]))
    assert detail_response.status_code == 404

    message_response = api_client.post(
        reverse("conversation-threads-messages", args=[thread.id]),
        {"body": "I should not be here."},
        format="json",
    )
    assert message_response.status_code == 404


@pytest.mark.django_db
def test_arbitrary_user_cannot_start_thread_for_unrelated_inquiry(
    api_client,
    other_user,
    inquiry,
):
    api_client.force_authenticate(other_user)

    response = api_client.post(
        reverse("conversation-threads-list"),
        {"property": str(inquiry.property_id), "inquiry": str(inquiry.id)},
        format="json",
    )

    assert response.status_code == 400
    assert "inquiry" in response.data


@pytest.mark.django_db
def test_user_cannot_start_contextless_thread_for_property(
    api_client,
    owner,
    property_listing,
):
    api_client.force_authenticate(owner)

    response = api_client.post(
        reverse("conversation-threads-list"),
        {"property": str(property_listing.id)},
        format="json",
    )

    assert response.status_code == 400
    assert "property" in response.data


@pytest.mark.django_db
def test_closed_thread_rejects_new_messages(api_client, buyer, inquiry):
    thread = ConversationThread.objects.create(
        property=inquiry.property,
        inquiry=inquiry,
        created_by=buyer,
        is_closed=True,
    )
    ConversationParticipant.objects.create(thread=thread, user=buyer)
    ConversationParticipant.objects.create(thread=thread, user=inquiry.property_owner)

    api_client.force_authenticate(buyer)
    response = api_client.post(
        reverse("conversation-threads-messages", args=[thread.id]),
        {"body": "Can you still see this?"},
        format="json",
    )

    assert response.status_code == 400
    assert Message.objects.count() == 0


@pytest.mark.django_db
def test_message_notifications_respect_recipient_preferences(
    api_client,
    owner,
    buyer,
    inquiry,
    monkeypatch,
):
    thread = ConversationThread.objects.create(
        property=inquiry.property,
        inquiry=inquiry,
        created_by=buyer,
    )
    ConversationParticipant.objects.create(thread=thread, user=buyer)
    ConversationParticipant.objects.create(thread=thread, user=owner)
    NotificationPreference.objects.create(user=owner, message_notifications=False)
    queued = []
    monkeypatch.setattr(
        "apps.notifications.services.queue_transactional_email",
        lambda **kwargs: queued.append(kwargs),
    )

    api_client.force_authenticate(buyer)
    response = api_client.post(
        reverse("conversation-threads-messages", args=[thread.id]),
        {"body": "Preference-aware message."},
        format="json",
    )

    assert response.status_code == 201
    assert Message.objects.filter(thread=thread).count() == 1
    assert not Notification.objects.filter(
        recipient=owner,
        notification_type=NotificationType.NEW_MESSAGE,
    ).exists()
    assert queued == []


@pytest.mark.django_db
def test_message_send_is_idempotent_for_same_client_message_id(api_client, owner, buyer, inquiry):
    thread = ConversationThread.objects.create(
        property=inquiry.property,
        inquiry=inquiry,
        created_by=buyer,
    )
    ConversationParticipant.objects.create(thread=thread, user=buyer)
    ConversationParticipant.objects.create(thread=thread, user=owner)
    client_message_id = "9d38b97e-b41f-484c-a424-6c507fbb2057"

    api_client.force_authenticate(buyer)
    first = api_client.post(
        reverse("conversation-threads-messages", args=[thread.id]),
        {"body": "Only once.", "client_message_id": client_message_id},
        format="json",
    )
    second = api_client.post(
        reverse("conversation-threads-messages", args=[thread.id]),
        {"body": "Only once.", "client_message_id": client_message_id},
        format="json",
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.data["id"] == second.data["id"]
    assert Message.objects.filter(thread=thread).count() == 1
    assert Notification.objects.filter(
        recipient=owner,
        notification_type=NotificationType.NEW_MESSAGE,
    ).count() == 1
    assert AuditLog.objects.filter(actor=buyer, action="message.sent").count() == 1
    assert RealtimeOutboxEvent.objects.filter(
        event_type=RealtimeOutboxEvent.EventType.MESSAGE_CREATED
    ).count() == 1


@pytest.mark.django_db
def test_invalid_client_message_id_is_rejected(api_client, buyer, inquiry):
    thread = ConversationThread.objects.create(
        property=inquiry.property,
        inquiry=inquiry,
        created_by=buyer,
    )
    ConversationParticipant.objects.create(thread=thread, user=buyer)
    ConversationParticipant.objects.create(thread=thread, user=inquiry.property_owner)

    api_client.force_authenticate(buyer)
    response = api_client.post(
        reverse("conversation-threads-messages", args=[thread.id]),
        {"body": "Bad id.", "client_message_id": "not-a-uuid"},
        format="json",
    )

    assert response.status_code == 400
    assert Message.objects.count() == 0


@pytest.mark.django_db
def test_message_create_rejects_empty_and_oversized_bodies(api_client, buyer, inquiry):
    thread = ConversationThread.objects.create(
        property=inquiry.property,
        inquiry=inquiry,
        created_by=buyer,
    )
    ConversationParticipant.objects.create(thread=thread, user=buyer)
    ConversationParticipant.objects.create(thread=thread, user=inquiry.property_owner)

    api_client.force_authenticate(buyer)
    empty = api_client.post(
        reverse("conversation-threads-messages", args=[thread.id]),
        {"body": "   "},
        format="json",
    )
    oversized = api_client.post(
        reverse("conversation-threads-messages", args=[thread.id]),
        {"body": "x" * 4001},
        format="json",
    )

    assert empty.status_code == 400
    assert oversized.status_code == 400
    assert Message.objects.count() == 0


@pytest.mark.django_db
def test_thread_messages_are_paginated_and_unread_counts_are_tracked(
    api_client, owner, buyer, inquiry
):
    thread = ConversationThread.objects.create(
        property=inquiry.property,
        inquiry=inquiry,
        created_by=buyer,
    )
    ConversationParticipant.objects.create(thread=thread, user=buyer)
    ConversationParticipant.objects.create(thread=thread, user=owner)
    Message.objects.create(thread=thread, sender=buyer, body="One")
    Message.objects.create(thread=thread, sender=buyer, body="Two")

    api_client.force_authenticate(owner)
    list_response = api_client.get(reverse("conversation-threads-list"))
    unread_response = api_client.get(reverse("conversation-threads-unread-count"))
    messages_response = api_client.get(reverse("conversation-threads-messages", args=[thread.id]))

    assert list_response.status_code == 200
    assert list_response.data["results"][0]["unread_count"] == 2
    assert unread_response.status_code == 200
    assert unread_response.data["unread_count"] == 2
    assert messages_response.status_code == 200
    assert "results" in messages_response.data

    mark_response = api_client.post(reverse("conversation-threads-mark-read", args=[thread.id]))
    assert mark_response.status_code == 200
    assert api_client.get(reverse("conversation-threads-unread-count")).data["unread_count"] == 0


@pytest.mark.django_db
def test_thread_messages_support_after_cursor(api_client, owner, buyer, inquiry):
    thread = ConversationThread.objects.create(
        property=inquiry.property,
        inquiry=inquiry,
        created_by=buyer,
    )
    ConversationParticipant.objects.create(thread=thread, user=buyer)
    ConversationParticipant.objects.create(thread=thread, user=owner)
    from apps.notifications.services import create_message

    first = create_message(thread=thread, sender=buyer, body="One")
    second = create_message(thread=thread, sender=buyer, body="Two")
    third = create_message(thread=thread, sender=owner, body="Three")

    api_client.force_authenticate(owner)
    response = api_client.get(
        reverse("conversation-threads-messages", args=[thread.id]),
        {"after": str(first.id)},
    )

    assert response.status_code == 200
    ids = [item["id"] for item in response.data["results"]]
    assert ids == [str(second.id), str(third.id)]


@pytest.mark.django_db
def test_message_send_and_mark_read_create_audit_events(api_client, owner, buyer, inquiry):
    thread = ConversationThread.objects.create(
        property=inquiry.property,
        inquiry=inquiry,
        created_by=buyer,
    )
    ConversationParticipant.objects.create(thread=thread, user=buyer)
    ConversationParticipant.objects.create(thread=thread, user=owner)

    api_client.force_authenticate(buyer)
    response = api_client.post(
        reverse("conversation-threads-messages", args=[thread.id]),
        {"body": "Audited message."},
        format="json",
    )
    assert response.status_code == 201
    assert AuditLog.objects.filter(actor=buyer, action="message.sent").exists()

    mark_response = api_client.post(reverse("conversation-threads-mark-read", args=[thread.id]))
    assert mark_response.status_code == 200
    assert AuditLog.objects.filter(actor=buyer, action="message.read").exists()


@pytest.mark.django_db
def test_transactional_email_provider_failure_does_not_raise(owner, monkeypatch):
    notification = Notification.objects.create(
        recipient=owner,
        notification_type=NotificationType.SYSTEM,
        title="System notice",
        body="A safe email body.",
    )

    class FailingProvider:
        def send(self, message):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "apps.notifications.services.get_email_provider",
        lambda: FailingProvider(),
    )

    from apps.notifications.services import send_notification_email_now

    assert send_notification_email_now(notification_id=notification.id) is False


@pytest.mark.django_db
def test_transactional_email_task_can_raise_for_retry(owner, monkeypatch):
    notification = Notification.objects.create(
        recipient=owner,
        notification_type=NotificationType.SYSTEM,
        title="System notice",
        body="A safe email body.",
    )

    class FailingProvider:
        def send(self, message):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(
        "apps.notifications.services.get_email_provider",
        lambda: FailingProvider(),
    )

    from apps.notifications.services import send_notification_email_now

    with pytest.raises(RuntimeError):
        send_notification_email_now(notification_id=notification.id, raise_on_failure=True)


@pytest.mark.django_db(transaction=True)
def test_realtime_outbox_failure_keeps_message_retryable(
    api_client, owner, buyer, inquiry, monkeypatch
):
    thread = ConversationThread.objects.create(
        property=inquiry.property,
        inquiry=inquiry,
        created_by=buyer,
    )
    ConversationParticipant.objects.create(thread=thread, user=buyer)
    ConversationParticipant.objects.create(thread=thread, user=owner)

    queued = []
    monkeypatch.setattr(
        "apps.notifications.services.queue_realtime_outbox_processing",
        lambda **kwargs: queued.append(kwargs) or True,
    )

    api_client.force_authenticate(buyer)
    response = api_client.post(
        reverse("conversation-threads-messages", args=[thread.id]),
        {"body": "Persist during Redis outage."},
        format="json",
    )

    assert response.status_code == 201
    message = Message.objects.get(id=response.data["id"])
    event = RealtimeOutboxEvent.objects.get(
        event_type=RealtimeOutboxEvent.EventType.MESSAGE_CREATED,
        aggregate_id=message.id,
    )

    def fail_publish(event):
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr("apps.notifications.services.publish_realtime_outbox_event", fail_publish)

    from apps.notifications.services import process_realtime_outbox_event_now

    assert process_realtime_outbox_event_now(event_id=event.id) is False
    event.refresh_from_db()
    assert event.status == RealtimeOutboxEvent.Status.FAILED
    assert event.attempt_count == 1
    assert Message.objects.filter(id=message.id).exists()


@pytest.mark.django_db(transaction=True)
def test_realtime_outbox_retry_can_deliver_failed_event(
    api_client, owner, buyer, inquiry, monkeypatch
):
    thread = ConversationThread.objects.create(
        property=inquiry.property,
        inquiry=inquiry,
        created_by=buyer,
    )
    ConversationParticipant.objects.create(thread=thread, user=buyer)
    ConversationParticipant.objects.create(thread=thread, user=owner)
    monkeypatch.setattr(
        "apps.notifications.services.queue_realtime_outbox_processing",
        lambda **kwargs: True,
    )
    api_client.force_authenticate(buyer)
    response = api_client.post(
        reverse("conversation-threads-messages", args=[thread.id]),
        {"body": "Retry me."},
        format="json",
    )
    event = RealtimeOutboxEvent.objects.get(aggregate_id=response.data["id"])
    event.status = RealtimeOutboxEvent.Status.FAILED
    event.next_attempt_at = None
    event.save(update_fields=["status", "next_attempt_at"])
    delivered = []
    monkeypatch.setattr(
        "apps.notifications.services.publish_realtime_outbox_event",
        lambda event: delivered.append(event.id),
    )

    from apps.notifications.services import process_due_realtime_outbox_events

    assert process_due_realtime_outbox_events(limit=10) >= 1
    event.refresh_from_db()
    assert event.status == RealtimeOutboxEvent.Status.DELIVERED
    assert event.id in delivered


@pytest.mark.django_db
def test_duplicate_thread_context_returns_existing_thread(api_client, owner, buyer, inquiry):
    api_client.force_authenticate(buyer)
    payload = {"property": str(inquiry.property_id), "inquiry": str(inquiry.id)}

    first = api_client.post(reverse("conversation-threads-list"), payload, format="json")
    second = api_client.post(reverse("conversation-threads-list"), payload, format="json")

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.data["id"] == second.data["id"]
    assert ConversationThread.objects.count() == 1


@pytest.mark.django_db
def test_websocket_message_throttle_is_user_scoped(settings, buyer):
    settings.WEBSOCKET_MESSAGE_RATE_LIMIT_COUNT = 1
    settings.WEBSOCKET_MESSAGE_RATE_LIMIT_WINDOW_SECONDS = 60

    from apps.notifications.throttling import websocket_message_send_allowed

    assert websocket_message_send_allowed(buyer.id) == (True, 60)
    assert websocket_message_send_allowed(buyer.id) == (False, 60)
