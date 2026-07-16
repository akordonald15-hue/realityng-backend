"""Shared fixtures for trust app tests."""

from __future__ import annotations

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.properties.choices import ListingType, PropertyStatus, PropertyType
from apps.properties.models import Property
from apps.trust.models import PropertyVerification, VerificationRequest


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="agent@example.com",
        password="StrOngPass123!",
        first_name="Agent",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="other-agent@example.com",
        password="StrOngPass123!",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="verification-admin@example.com",
        password="StrOngPass123!",
        is_staff=True,
    )


@pytest.fixture
def property_listing(user):
    return Property.objects.create(
        owner=user,
        title="Approved Ikoyi Maisonette",
        description="A finished maisonette with strong access roads.",
        property_type=PropertyType.HOUSE,
        listing_type=ListingType.SALE,
        price="120000000.00",
        currency="NGN",
        country="Nigeria",
        state="Lagos",
        city="Ikoyi",
        address="Bourdillon Road",
        bedrooms=4,
        bathrooms=5,
        parking_spaces=3,
        floor_area="340.00",
        status=PropertyStatus.APPROVED,
    )


@pytest.fixture
def verification_request(user):
    return VerificationRequest.objects.create(
        user=user,
        verification_type="agent",
        status="pending",
        business_name="Acme Realty Ltd",
        phone_number="+2348012345678",
    )


@pytest.fixture
def property_verification(user, property_listing):
    return PropertyVerification.objects.create(
        property=property_listing,
        submitted_by=user,
        status="pending",
    )


@pytest.fixture
def valid_pdf_file():
    return SimpleUploadedFile(
        "cac-certificate.pdf",
        b"%PDF-1.4\n%fake but valid header for testing\n",
        content_type="application/pdf",
    )


@pytest.fixture
def invalid_pdf_file():
    """A file with a .pdf extension and declared PDF content type,
    but whose actual bytes are not a real PDF -- tests real-content
    verification, not just extension/MIME trust."""
    return SimpleUploadedFile(
        "fake-cac-certificate.pdf",
        b"MZ\x90\x00\x03\x00\x00\x00this-is-not-a-real-pdf",
        content_type="application/pdf",
    )


@pytest.fixture
def oversized_file(settings):
    settings.VERIFICATION_DOCUMENT_MAX_SIZE_MB = 1
    content = b"%PDF-1.4\n" + (b"0" * (2 * 1024 * 1024))
    return SimpleUploadedFile("large-document.pdf", content, content_type="application/pdf")


@pytest.fixture
def disallowed_extension_file():
    return SimpleUploadedFile(
        "script.exe",
        b"MZ\x90\x00\x03\x00\x00\x00",
        content_type="application/x-msdownload",
    )


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()
