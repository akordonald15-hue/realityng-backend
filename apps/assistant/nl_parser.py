"""Natural-language query parsing into validated property search filters.

Uses the AI provider's tool-calling to extract structured filters from a
free-text query, then re-validates the extraction with a DRF serializer
before it is ever used to build a queryset. The tool schema's enums are
kept in lockstep with apps.properties.choices; the serializer is a second,
independent line of defense in case the provider extraction is malformed
or hallucinated.
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers

from apps.assistant.providers import AIProvider, AIProviderError, ProviderMessage, get_provider
from apps.properties.choices import ListingType, PropertyType

EXTRACT_FILTERS_TOOL_NAME = "extract_property_search_filters"

EXTRACT_FILTERS_TOOL = {
    "name": EXTRACT_FILTERS_TOOL_NAME,
    "description": (
        "Extract structured property search filters from the user's natural-language "
        "query. Only include a field if the user's query actually implies it. Omit "
        "any field you are not confident about rather than guessing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "City or locality mentioned, e.g. 'Lekki', 'Ikeja'.",
            },
            "property_type": {
                "type": "string",
                "enum": [choice.value for choice in PropertyType],
            },
            "listing_type": {
                "type": "string",
                "enum": [choice.value for choice in ListingType],
            },
            "min_price": {"type": "number", "minimum": 0},
            "max_price": {"type": "number", "minimum": 0},
            "min_bedrooms": {"type": "integer", "minimum": 0},
            "min_bathrooms": {"type": "integer", "minimum": 0},
        },
        "additionalProperties": False,
    },
}

NL_PARSER_SYSTEM_PROMPT = (
    "You extract structured real-estate search filters from a user's message. "
    "Always call the extract_property_search_filters tool. Only set fields the "
    "user's message actually implies; leave everything else out."
)


class NLParseError(Exception):
    """Raised when the query cannot be parsed into valid filters."""


class PropertySearchFilterSerializer(serializers.Serializer):
    city = serializers.CharField(max_length=100, required=False, allow_blank=False)
    property_type = serializers.ChoiceField(choices=PropertyType.choices, required=False)
    listing_type = serializers.ChoiceField(choices=ListingType.choices, required=False)
    min_price = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0"), required=False)
    max_price = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0"), required=False)
    min_bedrooms = serializers.IntegerField(min_value=0, required=False)
    min_bathrooms = serializers.IntegerField(min_value=0, required=False)

    def validate(self, attrs):
        min_price = attrs.get("min_price")
        max_price = attrs.get("max_price")
        if min_price is not None and max_price is not None and min_price > max_price:
            attrs.pop("min_price", None)
            attrs.pop("max_price", None)
        return attrs


def parse_query_to_filters(query: str, provider: AIProvider | None = None) -> dict:
    """Parse a free-text search query into a dict of validated property filters.

    Returns an empty dict (never raises) if the provider is unavailable or
    extraction fails outright — callers should treat that as "no filters
    could be confidently extracted" and fall back to an unfiltered or
    standard-search experience rather than surfacing an error to the user.
    """
    query = (query or "").strip()
    if not query:
        return {}

    provider = provider or get_provider("anthropic")
    if not provider.is_configured():
        return {}

    messages = [ProviderMessage(role="user", content=query)]

    try:
        response = provider.send_message(
            messages,
            system=NL_PARSER_SYSTEM_PROMPT,
            tools=[EXTRACT_FILTERS_TOOL],
            tool_choice={"type": "tool", "name": EXTRACT_FILTERS_TOOL_NAME},
            max_tokens=512,
        )
    except AIProviderError:
        return {}

    tool_call = next(
        (call for call in response.tool_calls if call["name"] == EXTRACT_FILTERS_TOOL_NAME),
        None,
    )
    if tool_call is None:
        return {}

    serializer = PropertySearchFilterSerializer(data=tool_call["input"])
    if not serializer.is_valid():
        return {}

    return {k: v for k, v in serializer.validated_data.items()}
