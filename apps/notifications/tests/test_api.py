from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.notifications.choices import NotificationType
from apps.notifications.models import (
    ConversationParticipant,
    ConversationThread,
    Message,
    Notification,
    NotificationPreference,
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
