from __future__ import annotations

import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework import serializers

from apps.notifications.models import ConversationParticipant, ConversationThread
from apps.notifications.services import (
    create_message,
    notification_group_name,
    thread_group_name,
)
from apps.notifications.throttling import websocket_message_send_allowed

WEBSOCKET_SUBPROTOCOL = "realityng.websocket.v1"
logger = logging.getLogger(__name__)


class AuthenticatedJsonConsumer(AsyncJsonWebsocketConsumer):
    @classmethod
    async def encode_json(cls, content):
        return DjangoJSONEncoder().encode(content)

    async def connect(self):
        if not self._is_authenticated():
            await self.close(code=4401)
            return
        await self.accept(subprotocol=_accepted_subprotocol(self.scope))

    def _is_authenticated(self) -> bool:
        user = self.scope.get("user")
        return bool(user and not isinstance(user, AnonymousUser) and user.is_authenticated)


class NotificationConsumer(AuthenticatedJsonConsumer):
    async def connect(self):
        if not self._is_authenticated():
            await self.close(code=4401)
            return
        self.group_name = notification_group_name(self.scope["user"].id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept(subprotocol=_accepted_subprotocol(self.scope))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification_created(self, event):
        await self.send_json(
            {
                "type": "notification.created",
                "notification": event["notification"],
                "unread_count": event["unread_count"],
            }
        )


class ConversationThreadConsumer(AuthenticatedJsonConsumer):
    async def connect(self):
        self.thread_id = self.scope["url_route"]["kwargs"]["thread_id"]
        if not self._is_authenticated():
            await self.close(code=4401)
            return
        if not await self._user_can_join_thread():
            logger.info(
                "websocket.thread_join.denied",
                extra={"thread_id": str(self.thread_id), "user_id": str(self.scope["user"].id)},
            )
            await self.close(code=4403)
            return
        self.group_name = thread_group_name(self.thread_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept(subprotocol=_accepted_subprotocol(self.scope))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get("type") != "message.send":
            await self._send_error("unsupported_event", "Unsupported WebSocket event.")
            return
        allowed, retry_after = await self._message_send_allowed()
        if not allowed:
            logger.info(
                "websocket.rate_limited",
                extra={"user_id": str(self.scope["user"].id), "thread_id": str(self.thread_id)},
            )
            await self._send_error(
                "rate_limited",
                {
                    "message": "Too many messages. Try again shortly.",
                    "retry_after_seconds": retry_after,
                },
            )
            return
        try:
            message = await self._create_message(
                content.get("body", ""),
                content.get("client_message_id"),
            )
        except serializers.ValidationError as exc:
            await self._send_error("validation_error", exc.detail)
            return
        await self.send_json(
            {
                "type": "message.accepted",
                "message_id": str(message.id),
                "client_message_id": str(message.client_message_id)
                if message.client_message_id
                else None,
            }
        )

    async def message_created(self, event):
        await self.send_json({"type": "message.created", "message": event["message"]})

    async def _send_error(self, code: str, detail):
        await self.send_json({"type": "error", "code": code, "detail": detail})

    @database_sync_to_async
    def _user_can_join_thread(self) -> bool:
        user = self.scope["user"]
        return ConversationParticipant.objects.filter(
            thread_id=self.thread_id,
            user=user,
        ).exists()

    @database_sync_to_async
    def _create_message(self, body: str, client_message_id: str | None):
        thread = ConversationThread.objects.get(id=self.thread_id)
        return create_message(
            thread=thread,
            sender=self.scope["user"],
            body=body,
            client_message_id=client_message_id,
        )

    @database_sync_to_async
    def _message_send_allowed(self) -> tuple[bool, int]:
        return websocket_message_send_allowed(self.scope["user"].id)


def _accepted_subprotocol(scope) -> str | None:
    protocols = scope.get("subprotocols", [])
    return WEBSOCKET_SUBPROTOCOL if WEBSOCKET_SUBPROTOCOL in protocols else None
