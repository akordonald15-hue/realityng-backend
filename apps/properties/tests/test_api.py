import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import AuditLog
from apps.properties.choices import ListingType, PropertyStatus, PropertyType
from apps.properties.models import Property


@pytest.mark.django_db
def test_authenticated_user_can_create_draft_property(api_client, user, property_payload):
    api_client.force_authenticate(user)

    response = api_client.post(reverse("properties-list"), property_payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    prop = Property.objects.get(id=response.data["id"])
    assert prop.owner == user
    assert prop.status == PropertyStatus.DRAFT


@pytest.mark.django_db
def test_owner_can_update_property(api_client, user, property_listing):
    api_client.force_authenticate(user)

    response = api_client.patch(
        reverse("properties-detail", args=[property_listing.slug]),
        {"price": "125000000.00"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    property_listing.refresh_from_db()
    assert str(property_listing.price) == "125000000.00"
    assert property_listing.status == PropertyStatus.DRAFT


@pytest.mark.django_db
def test_non_owner_cannot_update_property(api_client, other_user, property_listing):
    api_client.force_authenticate(other_user)

    response = api_client.patch(
        reverse("properties-detail", args=[property_listing.slug]),
        {"price": "125000000.00"},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_admin_can_update_any_property(api_client, admin_user, property_listing):
    api_client.force_authenticate(admin_user)

    response = api_client.patch(
        reverse("properties-detail", args=[property_listing.slug]),
        {"featured": True},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    property_listing.refresh_from_db()
    assert property_listing.featured is True


@pytest.mark.django_db
def test_owner_can_submit_property_for_review(api_client, user, property_listing):
    property_listing.status = PropertyStatus.DRAFT
    property_listing.save(update_fields=["status"])
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("properties-submit-for-review", args=[property_listing.slug]),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    property_listing.refresh_from_db()
    assert property_listing.status == PropertyStatus.PENDING_REVIEW
    assert AuditLog.objects.filter(
        action="property.submitted",
        entity_id=property_listing.id,
    ).exists()


@pytest.mark.django_db
def test_only_admin_can_approve_property(api_client, user, admin_user, property_listing):
    property_listing.status = PropertyStatus.PENDING_REVIEW
    property_listing.save(update_fields=["status"])
    api_client.force_authenticate(user)

    owner_response = api_client.post(
        reverse("properties-approve", args=[property_listing.slug]),
        {},
        format="json",
    )
    assert owner_response.status_code == status.HTTP_403_FORBIDDEN

    api_client.force_authenticate(admin_user)
    admin_response = api_client.post(
        reverse("properties-approve", args=[property_listing.slug]),
        {},
        format="json",
    )

    assert admin_response.status_code == status.HTTP_200_OK
    property_listing.refresh_from_db()
    assert property_listing.status == PropertyStatus.APPROVED
    assert AuditLog.objects.filter(
        action="property.approved",
        entity_id=property_listing.id,
    ).exists()


@pytest.mark.django_db
def test_admin_can_reject_property(api_client, admin_user, property_listing):
    property_listing.status = PropertyStatus.PENDING_REVIEW
    property_listing.save(update_fields=["status"])
    api_client.force_authenticate(admin_user)

    response = api_client.post(
        reverse("properties-reject", args=[property_listing.slug]),
        {"reason": "Missing proof of ownership"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    property_listing.refresh_from_db()
    assert property_listing.status == PropertyStatus.REJECTED


@pytest.mark.django_db
def test_public_endpoint_returns_only_approved_properties(
    api_client,
    user,
    property_listing,
    property_payload,
):
    Property.objects.create(owner=user, status=PropertyStatus.DRAFT, **property_payload)

    response = api_client.get(reverse("public-properties-list"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["slug"] == property_listing.slug


@pytest.mark.django_db
def test_public_endpoint_filters_searches_and_orders(api_client, user, property_payload):
    Property.objects.create(
        owner=user,
        status=PropertyStatus.APPROVED,
        title="Budget Abuja Apartment",
        description="Affordable apartment in Wuse.",
        property_type=PropertyType.APARTMENT,
        listing_type=ListingType.RENT,
        price="1500000.00",
        currency="NGN",
        country="Nigeria",
        state="FCT",
        city="Abuja",
        address="Wuse 2",
        bedrooms=2,
        bathrooms=2,
        floor_area="100.00",
    )
    Property.objects.create(
        owner=user,
        status=PropertyStatus.APPROVED,
        title="Luxury Lagos House",
        description="Detached house in Ikoyi.",
        property_type=PropertyType.HOUSE,
        listing_type=ListingType.SALE,
        price="220000000.00",
        currency="NGN",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        address="Ikoyi",
        bedrooms=5,
        bathrooms=5,
        floor_area="420.00",
    )

    response = api_client.get(
        reverse("public-properties-list"),
        {
            "search": "Apartment",
            "city": "Abuja",
            "property_type": PropertyType.APARTMENT,
            "listing_type": ListingType.RENT,
            "min_price": "1000000",
            "max_price": "2000000",
            "ordering": "price",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["title"] == "Budget Abuja Apartment"
