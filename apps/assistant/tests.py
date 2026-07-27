from __future__ import annotations

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.assistant.models import AIConversation
from apps.assistant.nl_parser import (
    NLParseUnavailable,
    parse_query_to_filters,
)
from apps.assistant.providers import ProviderResponse
from apps.assistant.tools import InvalidToolInputError, execute_tool
from apps.properties.choices import ListingType, PropertyStatus, PropertyType
from apps.properties.models import Property


class FakeProvider:
    def __init__(self, *, configured: bool = True, tool_input: dict | None = None):
        self.configured = configured
        self.tool_input = tool_input or {}

    def is_configured(self) -> bool:
        return self.configured

    def send_message(self, *args, **kwargs) -> ProviderResponse:
        return ProviderResponse(
            content="",
            tool_calls=[
                {
                    "id": "toolu_1",
                    "name": "extract_property_search_filters",
                    "input": self.tool_input,
                }
            ],
        )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="buyer@example.com",
        password="StrOngPass123!",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="other-buyer@example.com",
        password="StrOngPass123!",
    )


@pytest.fixture
def property_owner(db):
    return User.objects.create_user(
        email="owner@example.com",
        password="StrOngPass123!",
    )


def create_property(owner: User, **overrides) -> Property:
    payload = {
        "owner": owner,
        "title": "Lekki Three Bedroom Apartment",
        "description": "A verified apartment near Admiralty Way.",
        "property_type": PropertyType.APARTMENT,
        "listing_type": ListingType.RENT,
        "price": "3500000.00",
        "currency": "NGN",
        "country": "Nigeria",
        "state": "Lagos",
        "city": "Lekki",
        "address": "Admiralty Way",
        "bedrooms": 3,
        "bathrooms": 3,
        "parking_spaces": 2,
        "status": PropertyStatus.APPROVED,
    }
    payload.update(overrides)
    return Property.objects.create(**payload)


def test_parser_validates_provider_filters():
    filters = parse_query_to_filters(
        "3 bedroom apartments in Lekki under 5m",
        provider=FakeProvider(
            tool_input={
                "city": "Lekki",
                "property_type": PropertyType.APARTMENT,
                "listing_type": ListingType.RENT,
                "max_price": "5000000",
                "min_bedrooms": 3,
            }
        ),
    )

    assert filters["city"] == "Lekki"
    assert filters["property_type"] == PropertyType.APARTMENT
    assert filters["listing_type"] == ListingType.RENT
    assert filters["min_bedrooms"] == 3


def test_parser_rejects_invalid_provider_filters():
    filters = parse_query_to_filters(
        "find castles on mars",
        provider=FakeProvider(tool_input={"property_type": "castle", "min_price": -1}),
    )

    assert filters == {}


def test_parser_can_fail_closed_when_provider_unavailable():
    with pytest.raises(NLParseUnavailable):
        parse_query_to_filters(
            "show properties in Lekki",
            provider=FakeProvider(configured=False),
            fail_closed=True,
        )


@pytest.mark.django_db
def test_search_tool_only_returns_approved_properties(property_owner):
    approved = create_property(property_owner, status=PropertyStatus.APPROVED)
    create_property(
        property_owner,
        title="Draft Lekki Apartment",
        status=PropertyStatus.DRAFT,
    )

    result = execute_tool("search_properties", {"city": "Lekki"})

    assert result["result_count"] == 1
    assert result["results"][0]["id"] == str(approved.id)


@pytest.mark.django_db
def test_compare_tool_rejects_unapproved_and_missing_properties(property_owner):
    approved = create_property(property_owner, status=PropertyStatus.APPROVED)
    draft = create_property(
        property_owner,
        title="Draft Ikoyi Duplex",
        status=PropertyStatus.DRAFT,
    )

    result = execute_tool(
        "compare_properties",
        {"property_ids": [str(approved.id), str(draft.id)]},
    )

    assert [item["id"] for item in result["properties"]] == [str(approved.id)]
    assert result["missing_property_ids"] == [str(draft.id)]


def test_tool_input_is_validated_before_execution():
    with pytest.raises(InvalidToolInputError):
        execute_tool("search_properties", {"property_type": "palace"})


@pytest.mark.django_db
def test_ai_search_returns_503_when_provider_is_unavailable(api_client, monkeypatch):
    monkeypatch.setattr(
        "apps.assistant.nl_parser.get_provider",
        lambda name: FakeProvider(configured=False),
    )

    response = api_client.post(
        "/api/v1/assistant/search/",
        {"query": "show me properties in Lekki"},
        format="json",
    )

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.data["error"] == "assistant_unavailable"


@pytest.mark.django_db
def test_user_cannot_retrieve_another_users_conversation(api_client, user, other_user):
    conversation = AIConversation.objects.create(user=other_user)
    api_client.force_authenticate(user=user)

    response = api_client.get(f"/api/v1/conversations/{conversation.id}/")

    assert response.status_code == status.HTTP_404_NOT_FOUND
