from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.choices import RoleName, UserRoleStatus
from apps.accounts.models import Role, User, UserRole
from apps.services.choices import ProviderStatus, ProviderType, SkillLevel
from apps.services.models import ProviderTrade, ServiceArea, ServiceProvider, TradeCategory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="artisan@example.com",
        password="Str0ngPass123!",
        first_name="Artisan",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="customer@example.com",
        password="Str0ngPass123!",
        first_name="Customer",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="services-admin@example.com",
        password="Str0ngPass123!",
        is_staff=True,
    )


@pytest.fixture
def artisan_role(db):
    return Role.objects.get(name=RoleName.ARTISAN)


@pytest.fixture
def approved_artisan_user(user, artisan_role):
    UserRole.objects.create(
        user=user,
        role=artisan_role,
        status=UserRoleStatus.APPROVED,
    )
    return user


@pytest.fixture
def test_image_file():
    def _make_image(name="portfolio.jpg", image_format="JPEG", content_type="image/jpeg"):
        image = Image.new("RGB", (16, 16), color=(32, 96, 160))
        buffer = BytesIO()
        image.save(buffer, format=image_format)
        return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)

    return _make_image


@pytest.fixture
def electrical_category(db):
    return TradeCategory.objects.get(slug="electrical")


@pytest.fixture
def plumbing_category(db):
    return TradeCategory.objects.get(slug="plumbing")


@pytest.fixture
def active_provider(user, artisan_role, electrical_category):
    UserRole.objects.create(
        user=user,
        role=artisan_role,
        status=UserRoleStatus.APPROVED,
    )
    provider = ServiceProvider.objects.create(
        user=user,
        provider_type=ProviderType.INDIVIDUAL,
        business_name="Bright Spark Electrical",
        headline="Verified electrical repairs across Lagos",
        biography="Residential wiring, inverter setup, and fault finding.",
        phone="+2348012345678",
        email="artisan@example.com",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        lga="Eti-Osa",
        neighborhood="Lekki",
        private_address="Private workshop address",
        display_location="Lekki, Lagos",
        verification_snapshot={
            "badges": [
                {
                    "label": "Identity Verified",
                    "status": "approved",
                    "verified_at": "2026-07-01",
                }
            ]
        },
        average_rating="4.70",
        completed_jobs_count=12,
        status=ProviderStatus.ACTIVE,
    )
    ProviderTrade.objects.create(
        provider=provider,
        category=electrical_category,
        is_primary=True,
        years_experience=8,
        skill_level=SkillLevel.EXPERT,
    )
    ServiceArea.objects.create(
        provider=provider,
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        lga="Eti-Osa",
        neighborhood="Lekki",
        service_radius_km=15,
    )
    return provider
