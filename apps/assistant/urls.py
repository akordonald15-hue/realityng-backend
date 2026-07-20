from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.assistant.views import AIConversationViewSet, AISearchView

router = DefaultRouter()
router.register("conversations", AIConversationViewSet, basename="ai-conversations")

urlpatterns = router.urls + [
    path("assistant/search/", AISearchView.as_view(), name="ai-search"),
]
