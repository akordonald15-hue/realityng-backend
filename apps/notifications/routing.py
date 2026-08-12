from __future__ import annotations

from django.urls import path

from apps.notifications.consumers import ConversationThreadConsumer, NotificationConsumer

websocket_urlpatterns = [
    path("ws/notifications/", NotificationConsumer.as_asgi()),
    path("ws/messages/threads/<uuid:thread_id>/", ConversationThreadConsumer.as_asgi()),
]
