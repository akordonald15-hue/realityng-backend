from __future__ import annotations

from django.conf import settings
from django.core.cache import cache


def websocket_message_send_allowed(user_id) -> tuple[bool, int]:
    limit = int(getattr(settings, "WEBSOCKET_MESSAGE_RATE_LIMIT_COUNT", 20))
    window = int(getattr(settings, "WEBSOCKET_MESSAGE_RATE_LIMIT_WINDOW_SECONDS", 10))
    if limit <= 0 or window <= 0:
        return True, 0
    key = f"ws-message-send:{user_id}"
    added = cache.add(key, 0, timeout=window)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window)
        count = 1
    if added:
        cache.touch(key, timeout=window)
    return count <= limit, window
