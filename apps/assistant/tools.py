"""Tool/action schema for the AI assistant.

Every tool the assistant can call is defined here alongside a dispatcher
that executes it against real data. Execution is scoped exactly like the
public property API (status=APPROVED only) so a tool call can never
surface private or unapproved listing data, regardless of what the model
requests.
"""

from __future__ import annotations

from apps.properties.choices import ListingType, PropertyStatus, PropertyType
from apps.properties.filters import PublicPropertyFilter
from apps.properties.models import Property
from apps.properties.serializers import PublicPropertySerializer

TOOL_RESULT_LIMIT = 10


class UnknownToolError(Exception):
    """Raised when the model calls a tool name we don't recognize."""


SEARCH_PROPERTIES_TOOL = {
    "name": "search_properties",
    "description": (
        "Search approved property listings by structured filters. Use this "
        "whenever the user wants to find properties matching some criteria."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string"},
            "property_type": {"type": "string", "enum": [c.value for c in PropertyType]},
            "listing_type": {"type": "string", "enum": [c.value for c in ListingType]},
            "min_price": {"type": "number", "minimum": 0},
            "max_price": {"type": "number", "minimum": 0},
            "min_bedrooms": {"type": "integer", "minimum": 0},
            "min_bathrooms": {"type": "integer", "minimum": 0},
        },
        "additionalProperties": False,
    },
}

COMPARE_PROPERTIES_TOOL = {
    "name": "compare_properties",
    "description": (
        "Fetch full structured details for 2-4 specific approved properties, "
        "by id, for side-by-side comparison. Use when the user asks to "
        "compare specific listings they already know the ids of (e.g. from "
        "a prior search_properties result in this conversation)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "property_ids": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 4,
            },
        },
        "required": ["property_ids"],
        "additionalProperties": False,
    },
}

NAVIGATE_TOOL = {
    "name": "navigate",
    "description": (
        "Point the user to a specific screen in the app after helping them "
        "find what they need. Use this to direct them to a property detail "
        "page, an application or inquiry flow, or full search results."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "enum": ["property_detail", "application", "inquiry", "search_results"],
            },
            "property_id": {"type": "string"},
        },
        "required": ["target"],
        "additionalProperties": False,
    },
}

TOOL_DEFINITIONS = [SEARCH_PROPERTIES_TOOL, COMPARE_PROPERTIES_TOOL, NAVIGATE_TOOL]


def _base_queryset():
    return (
        Property.objects.filter(status=PropertyStatus.APPROVED)
        .select_related("owner")
        .prefetch_related("images")
    )


def _execute_search_properties(tool_input: dict) -> dict:
    base_queryset = _base_queryset()
    queryset = PublicPropertyFilter(tool_input, queryset=base_queryset).qs
    results = queryset[:TOOL_RESULT_LIMIT]
    return {
        "result_count": queryset.count(),
        "results": PublicPropertySerializer(results, many=True).data,
    }


def _execute_compare_properties(tool_input: dict) -> dict:
    property_ids = tool_input.get("property_ids") or []
    properties = list(_base_queryset().filter(id__in=property_ids))
    found_ids = {str(p.id) for p in properties}
    missing = [pid for pid in property_ids if pid not in found_ids]
    return {
        "properties": PublicPropertySerializer(properties, many=True).data,
        "missing_property_ids": missing,
    }


def _execute_navigate(tool_input: dict) -> dict:
    target = tool_input.get("target")
    property_id = tool_input.get("property_id")

    path_map = {
        "search_results": "/properties",
        "property_detail": f"/properties/{property_id}" if property_id else None,
        "application": f"/properties/{property_id}/apply" if property_id else "/applications",
        "inquiry": f"/properties/{property_id}/inquire" if property_id else None,
    }
    return {"target": target, "property_id": property_id, "path": path_map.get(target)}


TOOL_EXECUTORS = {
    "search_properties": _execute_search_properties,
    "compare_properties": _execute_compare_properties,
    "navigate": _execute_navigate,
}


def execute_tool(name: str, tool_input: dict) -> dict:
    """Execute a tool call by name and return a JSON-serializable result."""
    executor = TOOL_EXECUTORS.get(name)
    if executor is None:
        raise UnknownToolError(f"Unknown tool: {name}")
    return executor(tool_input or {})
