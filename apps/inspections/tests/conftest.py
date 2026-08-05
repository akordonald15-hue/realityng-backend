from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.choices import RoleName, UserRoleStatus
from apps.accounts.models import Role, User, UserRole
from apps.inspections.choices import InspectorVerificationStatus
from apps.inspections.models import InspectorProfile
from apps.properties.choices import ListingType, PropertyStatus, PropertyType
from apps.properties.models import Property


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def owner(db):
    return User.objects.create_user(
        email="inspection-owner@example.com",
        password="Str0ngPass123!",
    )


@pytest.fixture
def buyer(db):
    return User.objects.create_user(
        email="inspection-buyer@example.com",
        password="Str0ngPass123!",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="inspection-other@example.com",
        password="Str0ngPass123!",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="inspection-admin@example.com",
        password="Str0ngPass123!",
        is_staff=True,
    )


@pytest.fixture
def inspector_user(db):
    user = User.objects.create_user(
        email="inspector@example.com",
        password="Str0ngPass123!",
    )
    role = Role.objects.get(name=RoleName.INSPECTOR)
    UserRole.objects.create(user=user, role=role, status=UserRoleStatus.APPROVED)
    InspectorProfile.objects.create(
        user=user,
        display_name="RealityNG Inspector",
        professional_title="Property Inspector",
        verification_status=InspectorVerificationStatus.APPROVED,
        active=True,
    )
    return user


@pytest.fixture
def landlord_owner(owner):
    role = Role.objects.get(name=RoleName.LANDLORD)
    UserRole.objects.create(user=owner, role=role, status=UserRoleStatus.APPROVED)
    return owner


@pytest.fixture
def approved_property(landlord_owner):
    return Property.objects.create(
        owner=landlord_owner,
        title="Approved Inspection Home",
        description="A property eligible for inspection.",
        property_type=PropertyType.HOUSE,
        listing_type=ListingType.SALE,
        price=Decimal("85000000.00"),
        currency="NGN",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        address="Victoria Island",
        bedrooms=4,
        bathrooms=4,
        parking_spaces=2,
        floor_area=Decimal("300.00"),
        status=PropertyStatus.APPROVED,
    )


@pytest.fixture
def inspection_payload(approved_property):
    return {
        "property_id": str(approved_property.id),
        "inspection_type": "general",
        "purpose": "Remote buyer due diligence",
        "description": "Please inspect the property condition.",
        "contact_phone": "+2348012345678",
        "contact_email": "buyer@example.com",
    }
