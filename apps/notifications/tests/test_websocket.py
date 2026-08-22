from decimal import Decimal

import pytest
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.notifications.consumers import WEBSOCKET_SUBPROTOCOL
from apps.notifications.models import (
    ConversationParticipant,
    ConversationThread,
    Message,
    Notification,
)
from apps.notifications.services import (
    create_message,
    notification_group_name,
    process_due_realtime_outbox_events,
)
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
    await sync_to_async(process_due_realtime_outbox_events)(limit=10)

    event = await communicator.receive_json_from(timeout=2)
    assert event["type"] == "message.created"
    assert event["message"]["body"] == "Realtime hello."
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=CHANNEL_LAYER_OVERRIDE)
async def test_thread_websocket_accepts_subprotocol_token(websocket_users, websocket_thread):
    owner, _, _ = websocket_users
    token = await sync_to_async(_token_for)(owner)
    communicator = WebsocketCommunicator(
        application,
        f"/ws/messages/threads/{websocket_thread.id}/",
        subprotocols=[WEBSOCKET_SUBPROTOCOL, f"access_token.{token}"],
    )

    connected, selected = await communicator.connect()

    assert connected is True
    assert selected == WEBSOCKET_SUBPROTOCOL
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=CHANNEL_LAYER_OVERRIDE)
async def test_thread_websocket_denies_anonymous_connection(websocket_thread):
    communicator = WebsocketCommunicator(
        application,
        f"/ws/messages/threads/{websocket_thread.id}/",
        subprotocols=[WEBSOCKET_SUBPROTOCOL],
    )

    connected, _ = await communicator.connect()

    assert connected is False


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=CHANNEL_LAYER_OVERRIDE, WEBSOCKET_ALLOW_QUERY_TOKEN=False)
async def test_thread_websocket_rejects_query_string_token(websocket_users, websocket_thread):
    owner, _, _ = websocket_users
    token = await sync_to_async(_token_for)(owner)
    communicator = WebsocketCommunicator(
        application,
        f"/ws/messages/threads/{websocket_thread.id}/?token={token}",
        subprotocols=[WEBSOCKET_SUBPROTOCOL],
    )

    connected, _ = await communicator.connect()

    assert connected is False


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
@override_settings(
    CHANNEL_LAYERS=CHANNEL_LAYER_OVERRIDE,
    WEBSOCKET_MESSAGE_RATE_LIMIT_COUNT=1,
    WEBSOCKET_MESSAGE_RATE_LIMIT_WINDOW_SECONDS=60,
)
async def test_thread_websocket_rate_limits_by_user(websocket_users, websocket_thread):
    owner, buyer, _ = websocket_users
    token = await sync_to_async(_token_for)(buyer)
    communicator = WebsocketCommunicator(
        application,
        f"/ws/messages/threads/{websocket_thread.id}/",
        subprotocols=[WEBSOCKET_SUBPROTOCOL, f"access_token.{token}"],
    )
    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.send_json_to(
        {
            "type": "message.send",
            "body": "First.",
            "client_message_id": "b82f650a-fcd1-4c79-b48b-e22ac2f26097",
        }
    )
    accepted = await communicator.receive_json_from(timeout=2)
    assert accepted["type"] == "message.accepted"

    await communicator.send_json_to(
        {
            "type": "message.send",
            "body": "Second.",
            "client_message_id": "c57a7f12-00df-4ec2-9f11-af586d1b060f",
        }
    )
    error = await communicator.receive_json_from(timeout=2)

    assert error["type"] == "error"
    assert error["code"] == "rate_limited"
    assert await sync_to_async(Message.objects.filter(thread=websocket_thread).count)() == 1
    assert await sync_to_async(
        Message.objects.filter(thread=websocket_thread, sender=owner).exists
    )() is False
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=CHANNEL_LAYER_OVERRIDE)
async def test_thread_websocket_rejects_sender_spoofing_and_invalid_bodies(
    websocket_users, websocket_thread
):
    owner, buyer, _ = websocket_users
    token = await sync_to_async(_token_for)(buyer)
    communicator = WebsocketCommunicator(
        application,
        f"/ws/messages/threads/{websocket_thread.id}/",
        subprotocols=[WEBSOCKET_SUBPROTOCOL, f"access_token.{token}"],
    )
    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.send_json_to(
        {
            "type": "message.send",
            "body": "",
            "sender": str(owner.id),
            "client_message_id": "145c8f23-38bd-4dfe-a084-a7f610af9c08",
        }
    )
    empty_error = await communicator.receive_json_from(timeout=2)
    await communicator.send_json_to(
        {
            "type": "message.send",
            "body": "x" * 5001,
            "sender": str(owner.id),
            "client_message_id": "4e1664ed-71ea-4922-904e-dcc80b40fab7",
        }
    )
    oversized_error = await communicator.receive_json_from(timeout=2)

    assert empty_error["code"] == "validation_error"
    assert oversized_error["code"] == "validation_error"
    assert await sync_to_async(Message.objects.filter(thread=websocket_thread).exists)() is False
    await communicator.disconnect()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=CHANNEL_LAYER_OVERRIDE)
async def test_websocket_and_http_retry_share_client_message_id(
    websocket_users, websocket_thread
):
    _, buyer, _ = websocket_users
    client_message_id = "7de7e5a8-b2c0-45dc-9c43-d4a593bb3240"
    token = await sync_to_async(_token_for)(buyer)
    communicator = WebsocketCommunicator(
        application,
        f"/ws/messages/threads/{websocket_thread.id}/",
        subprotocols=[WEBSOCKET_SUBPROTOCOL, f"access_token.{token}"],
    )
    connected, _ = await communicator.connect()
    assert connected is True

    await communicator.send_json_to(
        {
            "type": "message.send",
            "body": "Same logical message.",
            "client_message_id": client_message_id,
        }
    )
    accepted = await communicator.receive_json_from(timeout=2)
    await communicator.disconnect()

    api_client = APIClient()
    api_client.force_authenticate(buyer)
    response = await sync_to_async(api_client.post)(
        f"/api/v1/messages/threads/{websocket_thread.id}/messages/",
        {"body": "Same logical message.", "client_message_id": client_message_id},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["id"] == accepted["message_id"]
    assert await sync_to_async(Message.objects.filter(thread=websocket_thread).count)() == 1


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


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@override_settings(CHANNEL_LAYERS=CHANNEL_LAYER_OVERRIDE)
async def test_notification_websocket_is_isolated_per_authenticated_user(websocket_users):
    owner, buyer, _ = websocket_users
    owner_token = await sync_to_async(_token_for)(owner)
    buyer_token = await sync_to_async(_token_for)(buyer)
    owner_socket = WebsocketCommunicator(
        application,
        "/ws/notifications/",
        subprotocols=[WEBSOCKET_SUBPROTOCOL, f"access_token.{owner_token}"],
    )
    buyer_socket = WebsocketCommunicator(
        application,
        "/ws/notifications/",
        subprotocols=[WEBSOCKET_SUBPROTOCOL, f"access_token.{buyer_token}"],
    )
    assert (await owner_socket.connect())[0] is True
    assert (await buyer_socket.connect())[0] is True

    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        notification_group_name(owner.id),
        {
            "type": "notification.created",
            "notification": {"id": "owner-only", "title": "Private notice"},
            "unread_count": 1,
        },
    )

    event = await owner_socket.receive_json_from(timeout=2)
    assert event["notification"]["id"] == "owner-only"
    assert await buyer_socket.receive_nothing(timeout=0.2) is True
    await owner_socket.disconnect()
    await buyer_socket.disconnect()
