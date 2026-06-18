from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.properties.choices import ListingType, PropertyStatus, PropertyType
from apps.properties.models import Property


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="owner@example.com",
        password="Str0ngPass123!",
        first_name="Owner",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="other@example.com",
        password="Str0ngPass123!",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="property-admin@example.com",
        password="Str0ngPass123!",
        is_staff=True,
    )


@pytest.fixture
def property_payload():
    return {
        "title": "Modern Lekki Apartment",
        "description": "A clean three-bedroom apartment near key roads.",
        "property_type": PropertyType.APARTMENT,
        "listing_type": ListingType.RENT,
        "price": "2500000.00",
        "currency": "NGN",
        "country": "Nigeria",
        "state": "Lagos",
        "city": "Lagos",
        "address": "Admiralty Way, Lekki Phase 1",
        "bedrooms": 3,
        "bathrooms": 3,
        "parking_spaces": 2,
        "floor_area": "180.00",
    }


@pytest.fixture
def property_listing(user):
    return Property.objects.create(
        owner=user,
        title="Approved Ikoyi Maisonette",
        description="A finished maisonette with strong access roads.",
        property_type=PropertyType.HOUSE,
        listing_type=ListingType.SALE,
        price=Decimal("120000000.00"),
        currency="NGN",
        country="Nigeria",
        state="Lagos",
        city="Ikoyi",
        address="Bourdillon Road",
        bedrooms=4,
        bathrooms=5,
        parking_spaces=3,
        floor_area=Decimal("340.00"),
        status=PropertyStatus.APPROVED,
    )
