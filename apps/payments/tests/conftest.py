"""Shared fixtures for payments app tests."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.payments.choices import (
    FinancingDocumentType,
    FinancingPartnerStatus,
    FinancingProductStatus,
    FinancingProductType,
)
from apps.payments.models import (
    FinancingDocumentRequirement,
    FinancingPartner,
    FinancingProduct,
    Transaction,
)
from apps.properties.choices import (
    ListingType,
    PropertyStatus,
    PropertyType,
    RentalApplicationStatus,
)
from apps.properties.models import Property, RentalApplication


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
def rental_application(property_listing, buyer, owner):
    return RentalApplication.objects.create(
        property=property_listing,
        applicant=buyer,
        property_owner=owner,
        full_name="Buyer Person",
        email="buyer@example.com",
        phone="08000000000",
        employment_status="employed",
        monthly_income=Decimal("1000000.00"),
        move_in_date="2030-01-01",
        status=RentalApplicationStatus.APPROVED,
    )


@pytest.fixture
def valid_proof_file():
    return SimpleUploadedFile(
        "receipt.pdf",
        b"%PDF-1.4\n%fake but valid header for test purposes",
        content_type="application/pdf",
    )


@pytest.fixture
def financing_partner(db):
    return FinancingPartner.objects.create(
        name="Manual Financing Partner",
        slug="manual-finance",
        status=FinancingPartnerStatus.ACTIVE,
        partner_type="manual",
        integration_mode="manual",
        supported_products=[FinancingProductType.RENT_FINANCE, FinancingProductType.MORTGAGE],
        supported_states=["Lagos", "Abuja"],
        minimum_amount=Decimal("100000.00"),
        maximum_amount=Decimal("50000000.00"),
        contact_policy="Manual partner handoff only.",
    )


@pytest.fixture
def financing_product(financing_partner):
    product = FinancingProduct.objects.create(
        partner=financing_partner,
        name="Rent Finance MVP",
        product_type=FinancingProductType.RENT_FINANCE,
        status=FinancingProductStatus.ACTIVE,
        currency="NGN",
        minimum_amount=Decimal("100000.00"),
        maximum_amount=Decimal("5000000.00"),
        minimum_tenor_months=1,
        maximum_tenor_months=12,
        requires_property=True,
        requires_income_documents=True,
        requires_bank_statement=True,
    )
    FinancingDocumentRequirement.objects.create(
        product=product,
        document_type=FinancingDocumentType.IDENTITY,
        required=True,
        description="Government-issued ID.",
    )
    FinancingDocumentRequirement.objects.create(
        product=product,
        document_type=FinancingDocumentType.BANK_STATEMENT,
        required=True,
        description="Recent bank statement.",
    )
    return product


@pytest.fixture
def valid_financing_document_file():
    return SimpleUploadedFile(
        "statement.pdf",
        b"%PDF-1.4\n%fake but valid header for financing document tests",
        content_type="application/pdf",
    )
