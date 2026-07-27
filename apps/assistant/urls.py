from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.assistant.views import AIConversationViewSet, AISearchView, AssistantConfigView

router = DefaultRouter()
router.register("conversations", AIConversationViewSet, basename="ai-conversations")

urlpatterns = router.urls + [
    path("assistant/config/", AssistantConfigView.as_view(), name="assistant-config"),
    path("assistant/search/", AISearchView.as_view(), name="ai-search"),
]
