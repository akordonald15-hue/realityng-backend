from rest_framework.routers import DefaultRouter

from apps.assistant.views import AIConversationViewSet

router = DefaultRouter()
router.register("conversations", AIConversationViewSet, basename="ai-conversations")

urlpatterns = router.urls
