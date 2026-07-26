import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import AuditLog
from apps.properties.choices import PropertyStatus
from apps.properties.models import Favorite, Property


@pytest.mark.django_db
def test_authenticated_user_can_save_property(api_client, user, property_listing):
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("favorites-list"),
        {"property_id": str(property_listing.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert Favorite.objects.filter(user=user, property=property_listing).exists()
    assert response.data["property"]["id"] == str(property_listing.id)
    assert response.data["property"]["is_favorited"] is True
    assert AuditLog.objects.filter(
        actor=user,
        action="property_favorited",
        entity_id=property_listing.id,
    ).exists()


@pytest.mark.django_db
def test_anonymous_user_cannot_save_property(api_client, property_listing):
    response = api_client.post(
        reverse("favorites-list"),
        {"property_id": str(property_listing.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_duplicate_favorite_is_rejected(api_client, user, property_listing):
    Favorite.objects.create(user=user, property=property_listing)
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("favorites-list"),
        {"property_id": str(property_listing.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert Favorite.objects.filter(user=user, property=property_listing).count() == 1


@pytest.mark.django_db
def test_deleted_property_cannot_be_saved(api_client, user, property_listing):
    property_id = property_listing.id
    property_listing.delete()
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("favorites-list"),
        {"property_id": str(property_id)},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert not Favorite.objects.filter(user=user, property_id=property_id).exists()


@pytest.mark.django_db
def test_user_can_list_only_own_favorites(api_client, user, other_user, property_listing):
    Favorite.objects.create(user=user, property=property_listing)
    Favorite.objects.create(user=other_user, property=property_listing)
    api_client.force_authenticate(user)

    response = api_client.get(reverse("favorites-list"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["property"]["slug"] == property_listing.slug


@pytest.mark.django_db
def test_user_can_remove_own_favorite(api_client, user, property_listing):
    Favorite.objects.create(user=user, property=property_listing)
    api_client.force_authenticate(user)

    response = api_client.delete(reverse("favorites-detail", args=[property_listing.id]))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Favorite.objects.filter(user=user, property=property_listing).exists()
    assert AuditLog.objects.filter(
        actor=user,
        action="property_unfavorited",
        entity_id=property_listing.id,
    ).exists()


@pytest.mark.django_db
def test_user_cannot_remove_another_users_favorite(
    api_client,
    user,
    other_user,
    property_listing,
):
    Favorite.objects.create(user=other_user, property=property_listing)
    api_client.force_authenticate(user)

    response = api_client.delete(reverse("favorites-detail", args=[property_listing.id]))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Favorite.objects.filter(user=other_user, property=property_listing).exists()


@pytest.mark.django_db
def test_public_property_marks_favorite_for_authenticated_user(
    api_client,
    user,
    property_listing,
):
    Favorite.objects.create(user=user, property=property_listing)
    api_client.force_authenticate(user)

    response = api_client.get(reverse("public-properties-detail", args=[property_listing.slug]))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_favorited"] is True


@pytest.mark.django_db
def test_public_property_marks_favorite_false_for_anonymous_user(api_client, property_listing):
    response = api_client.get(reverse("public-properties-detail", args=[property_listing.slug]))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_favorited"] is False


@pytest.mark.django_db
def test_dashboard_summary_counts_saved_active_and_draft_properties(
    api_client,
    user,
    property_listing,
    property_payload,
):
    Favorite.objects.create(user=user, property=property_listing)
    Property.objects.create(owner=user, status=PropertyStatus.DRAFT, **property_payload)
    api_client.force_authenticate(user)

    response = api_client.get(reverse("dashboard-summary"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data.items() >= {
        "saved_properties_count": 1,
        "active_listings_count": 1,
        "draft_listings_count": 1,
    }.items()
