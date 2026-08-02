"""Shared fixtures for payments app tests."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.payments.models import Transaction
from apps.properties.choices import ListingType, PropertyStatus, PropertyType
from apps.properties.models import Property


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def buyer(db):
    return User.objects.create_user(
        email="buyer@example.com", password="StrOngPass123!", first_name="Buyer",
    )


@pytest.fixture
def owner(db):
    return User.objects.create_user(
        email="owner@example.com", password="StrOngPass123!", first_name="Owner",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(email="other@example.com", password="StrOngPass123!")


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="payments-admin@example.com", password="StrOngPass123!", is_staff=True,
    )


@pytest.fixture
def property_listing(owner):
    return Property.objects.create(
        owner=owner,
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
        status=PropertyStatus.APPROVED,
    )


@pytest.fixture
def transaction(property_listing, buyer, owner):
    return Transaction.objects.create(property=property_listing, buyer=buyer, owner=owner)


@pytest.fixture
def valid_proof_file():
    return SimpleUploadedFile(
        "receipt.pdf",
        b"%PDF-1.4\n%fake but valid header for test purposes",
        content_type="application/pdf",
    )
