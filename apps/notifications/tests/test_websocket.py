from decimal import Decimal

import pytest
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.test import override_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.notifications.consumers import WEBSOCKET_SUBPROTOCOL
from apps.notifications.models import ConversationParticipant, ConversationThread, Notification
from apps.notifications.services import create_message, notification_group_name
from apps.properties.choices import InquiryType, ListingType, PropertyStatus, PropertyType
from apps.properties.models import Inquiry, Property
from config.asgi import application

CHANNEL_LAYER_OVERRIDE = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}


@pytest.fixture
def websocket_users(db):
    owner = User.objects.create_user(email="ws-owner@example.com", password="Pass12345!")
    buyer = User.objects.create_user(email="ws-buyer@example.com", password="Pass12345!")
    other = User.objects.create_user(email="ws-other@example.com", password="Pass12345!")
    return owner, buyer, other


@pytest.fixture
def websocket_thread(websocket_users):
    owner, buyer, _ = websocket_users
    prop = Property.objects.create(
        owner=owner,
        title="Realtime Lekki Terrace",
        description="A verified realtime terrace.",
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
        status=PropertyStatus.APPROVED,
    )
    inquiry = Inquiry.objects.create(
        property=prop,
        interested_user=buyer,
        property_owner=owner,
        inquiry_type=InquiryType.RENT,
        message="Can we talk?",
    )
    thread = ConversationThread.objects.create(property=prop, inquiry=inquiry, created_by=buyer)
    ConversationParticipant.objects.create(thread=thread, user=buyer)
    ConversationParticipant.objects.create(thread=thread, user=owner)
    return thread


def _token_for(user):
    return str(RefreshToken.for_user(user).access_token)


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=CHANNEL_LAYER_OVERRIDE)
async def test_thread_websocket_delivers_messages_to_participants(
    websocket_users, websocket_thread
):
    owner, buyer, _ = websocket_users
    token = await sync_to_async(_token_for)(owner)
    communicator = WebsocketCommunicator(
        application,
        f"/ws/messages/threads/{websocket_thread.id}/",
        subprotocols=[WEBSOCKET_SUBPROTOCOL, f"access_token.{token}"],
    )
    connected, _ = await communicator.connect()
    assert connected is True

    await sync_to_async(create_message)(
        thread=websocket_thread,
        sender=buyer,
        body="Realtime hello.",
    )

    event = await communicator.receive_json_from(timeout=2)
    assert event["type"] == "message.created"
    assert event["message"]["body"] == "Realtime hello."
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=CHANNEL_LAYER_OVERRIDE)
async def test_thread_websocket_denies_non_participants(websocket_users, websocket_thread):
    _, _, other = websocket_users
    token = await sync_to_async(_token_for)(other)
    communicator = WebsocketCommunicator(
        application,
        f"/ws/messages/threads/{websocket_thread.id}/",
        subprotocols=[WEBSOCKET_SUBPROTOCOL, f"access_token.{token}"],
    )
    connected, _ = await communicator.connect()
    assert connected is False


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=CHANNEL_LAYER_OVERRIDE)
async def test_notification_websocket_delivers_user_notifications(websocket_users):
    owner, _, _ = websocket_users
    token = await sync_to_async(_token_for)(owner)
    communicator = WebsocketCommunicator(
        application,
        "/ws/notifications/",
        subprotocols=[WEBSOCKET_SUBPROTOCOL, f"access_token.{token}"],
    )
    connected, _ = await communicator.connect()
    assert connected is True

    notification = await sync_to_async(Notification.objects.create)(
        recipient=owner,
        notification_type="system",
        title="Realtime notice",
    )
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        notification_group_name(owner.id),
        {
            "type": "notification.created",
            "notification": {"id": str(notification.id), "title": notification.title},
            "unread_count": 1,
        },
    )

    event = await communicator.receive_json_from(timeout=2)
    assert event["type"] == "notification.created"
    assert event["notification"]["title"] == "Realtime notice"
    assert event["unread_count"] == 1
    await communicator.disconnect()
