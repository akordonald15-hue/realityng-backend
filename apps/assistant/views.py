import json
import logging

from django.core.cache import cache
from django.db.models import Count, F
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.assistant.demo import DEMO_SUGGESTED_PROMPTS, SUPPORTED_DEMO_TOPICS
from apps.assistant.models import AIConversation, AIMessage
from apps.assistant.nl_parser import NLParseUnavailable, parse_query_to_filters
from apps.assistant.prompts import CONVERSATION_SYSTEM_PROMPT
from apps.assistant.providers import (
    AIProviderError,
    ProviderMessage,
    get_active_provider_mode,
    get_provider,
)
from apps.assistant.serializers import (
    AIConversationDetailSerializer,
    AIConversationSerializer,
    AIMessageSerializer,
    AISearchQuerySerializer,
    AssistantConfigSerializer,
    SendMessageSerializer,
)
from apps.assistant.tools import TOOL_DEFINITIONS, execute_tool
from apps.properties.choices import PropertyStatus
from apps.properties.filters import PublicPropertyFilter
from apps.properties.models import Property
from apps.properties.serializers import PublicPropertySerializer
from apps.properties.views import ActionScopedThrottleMixin

logger = logging.getLogger(__name__)

SESSION_CACHE_TTL_SECONDS = 30 * 60
SESSION_CACHE_MAX_MESSAGES = 20
AI_SEARCH_RESULT_LIMIT = 20
MAX_TOOL_ROUNDS = 2


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
        if getattr(self, "swagger_fake_view", False):
            return AIConversation.objects.none()
        queryset = AIConversation.objects.filter(user=self.request.user)
        if self.action == "retrieve":
            return queryset.prefetch_related("messages")
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AIConversationDetailSerializer
        return AIConversationSerializer

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except AIProviderError:
            return _unavailable_response()

    def perform_create(self, serializer):
        provider_mode = get_active_provider_mode()
        if provider_mode == AIConversation.Provider.DISABLED:
            raise AIProviderError("AI assistant is disabled.")
        serializer.save(
            user=self.request.user,
            status=AIConversation.Status.ACTIVE,
            provider=provider_mode,
        )

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

        plain_history = self._get_session_history(conversation)
        provider_messages = list(plain_history) + [
            ProviderMessage(role="user", content=user_content)
        ]

        provider = get_provider(conversation.provider)
        if not provider.is_configured():
            logger.warning(
                "AI provider %s not configured; falling back for conversation %s",
                conversation.provider,
                conversation.id,
            )
            return _unavailable_response()

        all_tool_calls = []
        tool_results_payload = []
        total_input_tokens = 0
        total_output_tokens = 0
        rounds = 0

        try:
            response = provider.send_message(
                provider_messages,
                system=CONVERSATION_SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                max_tokens=1024,
            )
            total_input_tokens += response.input_tokens or 0
            total_output_tokens += response.output_tokens or 0

            while response.tool_calls and rounds < MAX_TOOL_ROUNDS:
                rounds += 1
                provider_messages.append(
                    ProviderMessage(
                        role="assistant",
                        content=response.content,
                        raw_content=response.content_blocks,
                    )
                )

                tool_result_blocks = []
                for call in response.tool_calls:
                    all_tool_calls.append(call)
                    try:
                        result = execute_tool(call["name"], call["input"])
                    except Exception:
                        logger.exception(
                            "Tool execution failed: %s for conversation %s",
                            call["name"],
                            conversation.id,
                        )
                        result = {"error": "tool_execution_failed"}
                    tool_results_payload.append(
                        {
                            "tool_use_id": call["id"],
                            "tool": call["name"],
                            "input": call["input"],
                            "result": result,
                        }
                    )
                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": call["id"],
                            "content": json.dumps(result, default=str),
                        }
                    )

                provider_messages.append(
                    ProviderMessage(role="user", content="", raw_content=tool_result_blocks)
                )
                response = provider.send_message(
                    provider_messages,
                    system=CONVERSATION_SYSTEM_PROMPT,
                    tools=TOOL_DEFINITIONS,
                    max_tokens=1024,
                )
                total_input_tokens += response.input_tokens or 0
                total_output_tokens += response.output_tokens or 0
        except AIProviderError:
            logger.exception("AI provider call failed for conversation %s", conversation.id)
            return _unavailable_response()

        if conversation.provider == AIConversation.Provider.DEMO and response.raw:
            tool_results_payload = response.raw.get("tool_results", [])

        assistant_message = AIMessage.objects.create(
            conversation=conversation,
            role=AIMessage.Role.ASSISTANT,
            content=response.content,
            tool_calls=all_tool_calls,
            tool_results=tool_results_payload,
            token_count=total_output_tokens or None,
        )

        AIConversation.objects.filter(pk=conversation.pk).update(
            total_input_tokens=F("total_input_tokens") + total_input_tokens,
            total_output_tokens=F("total_output_tokens") + total_output_tokens,
        )

        logger.info(
            "ai_assistant_usage",
            extra={
                "conversation_id": str(conversation.id),
                "provider": conversation.provider,
                "tool_rounds": rounds,
                "tool_call_count": len(all_tool_calls),
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
            },
        )

        new_plain_history = plain_history + [
            ProviderMessage(role="user", content=user_content),
            ProviderMessage(role="assistant", content=response.content),
        ]
        self._set_session_history(conversation, new_plain_history)

        return Response(
            {
                "user_message": AIMessageSerializer(user_message).data,
                "assistant_message": AIMessageSerializer(assistant_message).data,
                "provider_metadata": {
                    "provider": conversation.provider,
                    "mode": conversation.provider,
                },
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

    def _set_session_history(
        self,
        conversation: AIConversation,
        history: list[ProviderMessage],
    ) -> None:
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
    serializer_class = AISearchQuerySerializer

    @extend_schema(
        request=AISearchQuerySerializer,
        responses={
            200: OpenApiResponse(description="Natural-language property search results."),
            503: OpenApiResponse(description="AI assistant provider unavailable."),
        },
    )
    def post(self, request):
        input_serializer = AISearchQuerySerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        query = input_serializer.validated_data["query"]

        try:
            extracted_filters = parse_query_to_filters(query, fail_closed=True)
        except NLParseUnavailable:
            logger.warning("AI search parser unavailable")
            return _unavailable_response()

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
                "provider_metadata": {
                    "provider": get_active_provider_mode(),
                    "mode": get_active_provider_mode(),
                },
                "results": PublicPropertySerializer(
                    results, many=True, context={"request": request}
                ).data,
            }
        )


class AssistantConfigView(APIView):
    permission_classes = [AllowAny]
    serializer_class = AssistantConfigSerializer

    @extend_schema(responses={200: AssistantConfigSerializer})
    def get(self, request):
        provider_mode = get_active_provider_mode()
        payload = {
            "enabled": provider_mode != AIConversation.Provider.DISABLED,
            "provider_mode": provider_mode,
            "label": (
                "RealityNG Demo Assistant"
                if provider_mode == AIConversation.Provider.DEMO
                else "RealityNG Assistant"
            ),
            "supported_topics": SUPPORTED_DEMO_TOPICS
            if provider_mode == AIConversation.Provider.DEMO
            else [
                "Property discovery",
                "Property comparison",
                "RealityNG workflow guidance",
            ],
            "suggested_prompts": DEMO_SUGGESTED_PROMPTS
            if provider_mode == AIConversation.Provider.DEMO
            else [
                "2-bedroom apartments in Lekki",
                "Compare properties I've saved",
                "How do I schedule a viewing?",
            ],
        }
        return Response(AssistantConfigSerializer(payload).data)
