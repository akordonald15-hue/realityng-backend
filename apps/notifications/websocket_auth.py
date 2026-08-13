from __future__ import annotations

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


class JwtAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope["user"] = await self._resolve_user(scope)
        return await self.app(scope, receive, send)

    @database_sync_to_async
    def _resolve_user(self, scope):
        token = _token_from_subprotocols(scope)
        if not token and getattr(settings, "WEBSOCKET_ALLOW_QUERY_TOKEN", False):
            token = _token_from_query_string(scope)
        if not token:
            logger.info("websocket.auth.failed", extra={"reason": "missing_token"})
            return AnonymousUser()
        try:
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            return jwt_auth.get_user(validated_token)
        except Exception:
            logger.info("websocket.auth.failed", extra={"reason": "invalid_token"})
            return AnonymousUser()


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)


def _token_from_subprotocols(scope) -> str:
    for protocol in scope.get("subprotocols", []):
        if isinstance(protocol, bytes):
            protocol = protocol.decode()
        if protocol.startswith("access_token."):
            return protocol.removeprefix("access_token.")
    return ""


def _token_from_query_string(scope) -> str:
    raw_query = scope.get("query_string", b"")
    if not raw_query:
        return ""
    query = parse_qs(raw_query.decode())
    return (query.get("token") or [""])[0]
