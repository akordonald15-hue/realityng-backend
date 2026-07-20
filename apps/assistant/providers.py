"""AI provider abstraction for the assistant app.

Add new providers by subclassing AIProvider and registering them in
PROVIDER_REGISTRY. Calling code should depend only on AIProvider,
never on a concrete provider class.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field

from django.conf import settings


class AIProviderError(Exception):
    """Raised when a provider call fails or is misconfigured."""


@dataclass
class ProviderMessage:
    """A single message in a conversation, in provider-agnostic form."""

    role: str  # "user" | "assistant" | "system" | "tool"
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    tool_results: list[dict] = field(default_factory=list)


@dataclass
class ProviderResponse:
    """The result of a single provider call, in provider-agnostic form."""

    content: str
    role: str = "assistant"
    tool_calls: list[dict] = field(default_factory=list)
    stop_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    raw: dict | None = None


class AIProvider(abc.ABC):
    """Abstract base class every AI provider integration must implement."""

    name: str = "base"

    @abc.abstractmethod
    def send_message(
        self,
        messages: list[ProviderMessage],
        *,
        system: str | None = None,
        tools: list[dict] | None = None,
        max_tokens: int = 1024,
    ) -> ProviderResponse:
        """Send a conversation to the provider and return its response.

        Implementations must raise AIProviderError on failure rather than
        leaking provider-specific exceptions to callers.
        """
        raise NotImplementedError

    def is_configured(self) -> bool:
        """Return whether this provider has the credentials it needs."""
        return True


class AnthropicProvider(AIProvider):
    """AIProvider implementation backed by the Anthropic Claude API."""

    name = "anthropic"
    default_model = "claude-sonnet-4-6"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or self.default_model
        self._client = None

    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def send_message(
        self,
        messages: list[ProviderMessage],
        *,
        system: str | None = None,
        tools: list[dict] | None = None,
        max_tokens: int = 1024,
    ) -> ProviderResponse:
        if not self.is_configured():
            raise AIProviderError("Anthropic provider is not configured: missing ANTHROPIC_API_KEY")

        import anthropic

        api_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role in ("user", "assistant")
        ]

        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": api_messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        try:
            response = self.client.messages.create(**kwargs)
        except anthropic.APIError as exc:
            raise AIProviderError(f"Anthropic API call failed: {exc}") from exc

        text_parts = [block.text for block in response.content if block.type == "text"]
        tool_calls = [
            {"id": block.id, "name": block.name, "input": block.input}
            for block in response.content
            if block.type == "tool_use"
        ]

        return ProviderResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            input_tokens=response.usage.input_tokens if response.usage else None,
            output_tokens=response.usage.output_tokens if response.usage else None,
            raw=response.model_dump() if hasattr(response, "model_dump") else None,
        )


PROVIDER_REGISTRY: dict[str, type[AIProvider]] = {
    AnthropicProvider.name: AnthropicProvider,
}


def get_provider(name: str, **kwargs) -> AIProvider:
    """Instantiate a registered provider by name."""
    try:
        provider_cls = PROVIDER_REGISTRY[name]
    except KeyError as exc:
        raise AIProviderError(f"Unknown AI provider: {name}") from exc
    return provider_cls(**kwargs)
