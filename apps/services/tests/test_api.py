import pytest
from django.urls import reverse
from rest_framework import status

from apps.services.choices import ProviderStatus, ProviderType
from apps.services.models import ServiceProvider


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
