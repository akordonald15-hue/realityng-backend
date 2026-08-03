import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import AuditLog
from apps.services.choices import ProviderStatus, ProviderType
from apps.services.models import PortfolioImage, ProviderTrade, ServiceProvider


@pytest.mark.django_db
def test_public_can_list_active_categories(api_client):
    response = api_client.get(reverse("service-categories-list"))

    assert response.status_code == status.HTTP_200_OK
    slugs = {category["slug"] for category in response.data}
    assert {"repairs", "utilities", "home-services", "construction-services"}.issubset(slugs)
    repairs = next(category for category in response.data if category["slug"] == "repairs")
    assert any(child["slug"] == "electrical" for child in repairs["children"])


@pytest.mark.django_db
def test_public_provider_list_returns_only_active_providers(
    api_client, active_provider, other_user
):
    ServiceProvider.objects.create(
        user=other_user,
        provider_type=ProviderType.INDIVIDUAL,
        business_name="Draft Cleaner",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        status=ProviderStatus.DRAFT,
    )

    response = api_client.get(reverse("service-providers-list"))

    assert response.status_code == status.HTTP_200_OK
    names = {provider["business_name"] for provider in response.data["results"]}
    assert "Bright Spark Electrical" in names
    assert "Draft Cleaner" not in names


@pytest.mark.django_db
def test_public_provider_list_filters_by_category_and_location(api_client, active_provider):
    response = api_client.get(
        reverse("service-providers-list"),
        {"category": "electrical", "state": "Lagos", "city": "Lagos", "lga": "Eti-Osa"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["slug"] == active_provider.slug


@pytest.mark.django_db
def test_public_provider_search_and_ordering(api_client, active_provider):
    response = api_client.get(
        reverse("service-providers-list"),
        {"search": "inverter", "ordering": "business_name"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["business_name"] == "Bright Spark Electrical"


@pytest.mark.django_db
def test_public_provider_detail_excludes_moderation_fields(api_client, active_provider):
    response = api_client.get(reverse("service-providers-detail", args=[active_provider.slug]))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["business_name"] == "Bright Spark Electrical"
    assert response.data["portfolio"]["message"]
    assert "private_address" not in response.data
    assert "verification_snapshot" not in response.data


@pytest.mark.django_db
def test_non_admin_cannot_retrieve_unpublished_provider(api_client, user, other_user):
    draft = ServiceProvider.objects.create(
        user=user,
        provider_type=ProviderType.INDIVIDUAL,
        business_name="Hidden Provider",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        status=ProviderStatus.DRAFT,
    )
    api_client.force_authenticate(user=other_user)

    response = api_client.get(reverse("service-providers-detail", args=[draft.slug]))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_admin_can_retrieve_unpublished_provider(api_client, admin_user, user):
    draft = ServiceProvider.objects.create(
        user=user,
        provider_type=ProviderType.INDIVIDUAL,
        business_name="Admin Visible Provider",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        status=ProviderStatus.DRAFT,
    )
    api_client.force_authenticate(user=admin_user)

    response = api_client.get(reverse("service-providers-detail", args=[draft.slug]))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["business_name"] == "Admin Visible Provider"


@pytest.mark.django_db
def test_approved_artisan_can_create_profile(api_client, approved_artisan_user):
    api_client.force_authenticate(user=approved_artisan_user)

    response = api_client.post(
        reverse("service-provider-profile"),
        {
            "provider_type": ProviderType.INDIVIDUAL,
            "business_name": "Reliable Repairs",
            "headline": "Fast home repairs",
            "biography": "Repairs for diaspora-owned homes.",
            "phone": "+2348011112222",
            "country": "Nigeria",
            "state": "Lagos",
            "city": "Lagos",
            "display_location": "Lagos",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == ProviderStatus.DRAFT
    assert AuditLog.objects.filter(action="service_provider.created").exists()


@pytest.mark.django_db
def test_non_provider_role_cannot_create_profile(api_client, other_user):
    api_client.force_authenticate(user=other_user)

    response = api_client.post(
        reverse("service-provider-profile"),
        {
            "business_name": "Not Allowed",
            "country": "Nigeria",
            "state": "Lagos",
            "city": "Lagos",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_provider_can_manage_trades_and_service_areas(
    api_client,
    active_provider,
    plumbing_category,
):
    active_provider.status = ProviderStatus.DRAFT
    active_provider.save(update_fields=["status", "updated_at"])
    api_client.force_authenticate(user=active_provider.user)

    trade_response = api_client.post(
        reverse("service-provider-profile-trades-list"),
        {
            "category_id": str(plumbing_category.id),
            "years_experience": 4,
            "skill_level": "expert",
            "is_primary": True,
        },
        format="json",
    )
    area_response = api_client.post(
        reverse("service-provider-profile-service-areas-list"),
        {
            "country": "Nigeria",
            "state": "Lagos",
            "city": "Ikeja",
            "service_radius_km": 20,
            "is_primary": True,
        },
        format="json",
    )

    assert trade_response.status_code == status.HTTP_201_CREATED
    assert area_response.status_code == status.HTTP_201_CREATED
    assert active_provider.trades.get(category=plumbing_category).is_primary is True
    assert active_provider.service_areas.get(city="Ikeja").is_primary is True


@pytest.mark.django_db
def test_provider_submission_requires_primary_trade_and_area(api_client, approved_artisan_user):
    provider = ServiceProvider.objects.create(
        user=approved_artisan_user,
        provider_type=ProviderType.INDIVIDUAL,
        business_name="Incomplete Provider",
        headline="Needs setup",
        biography="Almost ready.",
        phone="+2348011112222",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        status=ProviderStatus.DRAFT,
    )
    api_client.force_authenticate(user=approved_artisan_user)

    response = api_client.post(reverse("service-provider-profile-submit"))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "primary_trade" in response.data["completion"]["missing"]
    assert provider.status == ProviderStatus.DRAFT


@pytest.mark.django_db
def test_complete_provider_can_submit_and_admin_can_approve(
    api_client,
    active_provider,
    admin_user,
):
    active_provider.status = ProviderStatus.DRAFT
    active_provider.save(update_fields=["status", "updated_at"])
    active_provider.service_areas.update(is_primary=True)
    api_client.force_authenticate(user=active_provider.user)

    submit_response = api_client.post(reverse("service-provider-profile-submit"))
    active_provider.refresh_from_db()

    assert submit_response.status_code == status.HTTP_200_OK
    assert active_provider.status == ProviderStatus.PENDING_REVIEW

    api_client.force_authenticate(user=admin_user)
    approve_response = api_client.post(
        reverse("service-admin-providers-approve", args=[active_provider.id]),
        {},
        format="json",
    )
    active_provider.refresh_from_db()

    assert approve_response.status_code == status.HTTP_200_OK
    assert active_provider.status == ProviderStatus.ACTIVE
    assert AuditLog.objects.filter(action="service_provider.approved").exists()


@pytest.mark.django_db
def test_admin_reject_and_request_info_require_messages(api_client, active_provider, admin_user):
    active_provider.status = ProviderStatus.PENDING_REVIEW
    active_provider.save(update_fields=["status", "updated_at"])
    api_client.force_authenticate(user=admin_user)

    reject_response = api_client.post(
        reverse("service-admin-providers-reject", args=[active_provider.id]),
        {},
        format="json",
    )
    info_response = api_client.post(
        reverse("service-admin-providers-request-info", args=[active_provider.id]),
        {},
        format="json",
    )

    assert reject_response.status_code == status.HTTP_400_BAD_REQUEST
    assert info_response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_suspended_provider_is_not_public(api_client, active_provider):
    active_provider.status = ProviderStatus.SUSPENDED
    active_provider.save(update_fields=["status", "updated_at"])

    response = api_client.get(reverse("service-providers-list"))

    names = {provider["business_name"] for provider in response.data["results"]}
    assert active_provider.business_name not in names


@pytest.mark.django_db
def test_portfolio_upload_cover_and_public_gallery(
    api_client,
    active_provider,
    test_image_file,
):
    active_provider.status = ProviderStatus.DRAFT
    active_provider.save(update_fields=["status", "updated_at"])
    api_client.force_authenticate(user=active_provider.user)

    upload_response = api_client.post(
        reverse("service-provider-profile-portfolio-list"),
        {"image": test_image_file("portfolio.jpg"), "caption": "Finished wiring"},
        format="multipart",
    )

    assert upload_response.status_code == status.HTTP_201_CREATED
    assert upload_response.data["is_cover"] is True
    assert PortfolioImage.objects.filter(provider=active_provider).count() == 1
    assert AuditLog.objects.filter(action="service_provider.portfolio_uploaded").exists()

    active_provider.status = ProviderStatus.ACTIVE
    active_provider.save(update_fields=["status", "updated_at"])
    public_response = api_client.get(
        reverse("service-providers-detail", args=[active_provider.slug])
    )

    assert public_response.status_code == status.HTTP_200_OK
    assert public_response.data["portfolio"]["items"][0]["caption"] == "Finished wiring"
    assert "image" not in public_response.data["portfolio"]["items"][0]


@pytest.mark.django_db
def test_portfolio_rejects_invalid_image_content(api_client, active_provider):
    active_provider.status = ProviderStatus.DRAFT
    active_provider.save(update_fields=["status", "updated_at"])
    api_client.force_authenticate(user=active_provider.user)

    response = api_client.post(
        reverse("service-provider-profile-portfolio-list"),
        {"image": SimpleUploadedFile("bad.jpg", b"not an image", content_type="image/jpeg")},
        format="multipart",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_provider_cannot_manage_another_provider_trade(
    api_client,
    active_provider,
    other_user,
    plumbing_category,
):
    other_provider = ServiceProvider.objects.create(
        user=other_user,
        provider_type=ProviderType.INDIVIDUAL,
        business_name="Other Provider",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
    )
    trade = ProviderTrade.objects.create(
        provider=other_provider,
        category=plumbing_category,
    )
    api_client.force_authenticate(user=active_provider.user)

    response = api_client.patch(
        reverse("service-provider-profile-trades-detail", args=[trade.id]),
        {"years_experience": 9},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
