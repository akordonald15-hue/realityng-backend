from __future__ import annotations

from rest_framework.routers import DefaultRouter

from apps.notifications.views import ConversationThreadViewSet, NotificationViewSet

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notifications")
router.register("messages/threads", ConversationThreadViewSet, basename="conversation-threads")

urlpatterns = router.urls
