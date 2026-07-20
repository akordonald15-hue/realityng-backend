import logging

from django.core.cache import cache
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.assistant.models import AIConversation, AIMessage
from apps.assistant.nl_parser import parse_query_to_filters
from apps.assistant.providers import AIProviderError, ProviderMessage, get_provider
from apps.assistant.serializers import (
    AIConversationDetailSerializer,
    AIConversationSerializer,
    AIMessageSerializer,
    AISearchQuerySerializer,
    SendMessageSerializer,
)
from apps.properties.choices import PropertyStatus
from apps.properties.filters import PublicPropertyFilter
from apps.properties.models import Property
from apps.properties.serializers import PublicPropertySerializer
from apps.properties.views import ActionScopedThrottleMixin

logger = logging.getLogger(__name__)

SESSION_CACHE_TTL_SECONDS = 30 * 60
SESSION_CACHE_MAX_MESSAGES = 20
AI_SEARCH_RESULT_LIMIT = 20


def _session_cache_key(conversation_id) -> str:
    return f"ai:session:{conversation_id}"


def _unavailable_response() -> Response:
    return Response(
        {
            "error": "assistant_unavailable",
            "detail": "The assistant is temporarily unavailable. Please use standard search.",
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


class AIConversationViewSet(
    ActionScopedThrottleMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    throttle_scope_by_action = {"send_message": "ai_assistant_message"}

    def get_queryset(self):
        return (
            AIConversation.objects.filter(user=self.request.user)
            .prefetch_related("messages")
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AIConversationDetailSerializer
        return AIConversationSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status=AIConversation.Status.ACTIVE)

    @action(detail=True, methods=["post"], url_path="messages")
    def send_message(self, request, pk=None):
        conversation = get_object_or_404(self.get_queryset(), pk=pk)

        input_serializer = SendMessageSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        user_content = input_serializer.validated_data["content"]

        user_message = AIMessage.objects.create(
            conversation=conversation,
            role=AIMessage.Role.USER,
            content=user_content,
        )

        history = self._get_session_history(conversation)
        history.append(ProviderMessage(role="user", content=user_content))

        provider = get_provider(conversation.provider)
        if not provider.is_configured():
            logger.warning(
                "AI provider %s not configured; falling back for conversation %s",
                conversation.provider,
                conversation.id,
            )
            return _unavailable_response()

        try:
            provider_response = provider.send_message(history)
        except AIProviderError:
            logger.exception("AI provider call failed for conversation %s", conversation.id)
            return _unavailable_response()

        assistant_message = AIMessage.objects.create(
            conversation=conversation,
            role=AIMessage.Role.ASSISTANT,
            content=provider_response.content,
            tool_calls=provider_response.tool_calls,
            token_count=provider_response.output_tokens,
        )

        history.append(ProviderMessage(role="assistant", content=provider_response.content))
        self._set_session_history(conversation, history)

        return Response(
            {
                "user_message": AIMessageSerializer(user_message).data,
                "assistant_message": AIMessageSerializer(assistant_message).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def _get_session_history(self, conversation: AIConversation) -> list[ProviderMessage]:
        cached = cache.get(_session_cache_key(conversation.id))
        if cached is not None:
            return [ProviderMessage(role=m["role"], content=m["content"]) for m in cached]

        recent = conversation.messages.filter(
            role__in=[AIMessage.Role.USER, AIMessage.Role.ASSISTANT]
        ).order_by("-created_at")[:SESSION_CACHE_MAX_MESSAGES]
        history = [
            ProviderMessage(role=m.role, content=m.content) for m in reversed(list(recent))
        ]
        self._set_session_history(conversation, history)
        return history

    def _set_session_history(self, conversation: AIConversation, history: list[ProviderMessage]) -> None:
        trimmed = history[-SESSION_CACHE_MAX_MESSAGES:]
        payload = [{"role": m.role, "content": m.content} for m in trimmed]
        cache.set(_session_cache_key(conversation.id), payload, timeout=SESSION_CACHE_TTL_SECONDS)


class AISearchView(APIView):
    """Natural-language property search.

    Parses the query into validated filters and applies them via the same
    PublicPropertyFilter used by the standard property search endpoint, so
    results are guaranteed to match what a manual filtered search would
    return. Falls back to unfiltered (still status=APPROVED-scoped) results
    if no filters could be confidently extracted, rather than erroring.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_assistant_message"

    def post(self, request):
        input_serializer = AISearchQuerySerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        query = input_serializer.validated_data["query"]

        extracted_filters = parse_query_to_filters(query)

        base_queryset = (
            Property.objects.filter(status=PropertyStatus.APPROVED)
            .select_related("owner")
            .annotate(image_count=Count("images"))
            .prefetch_related("images")
        )
        filtered_queryset = PublicPropertyFilter(extracted_filters, queryset=base_queryset).qs
        results = filtered_queryset[:AI_SEARCH_RESULT_LIMIT]

        return Response(
            {
                "query": query,
                "extracted_filters": extracted_filters,
                "result_count": filtered_queryset.count(),
                "results": PublicPropertySerializer(
                    results, many=True, context={"request": request}
                ).data,
            }
        )
