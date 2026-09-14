import pytest
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import AuditLog
from apps.properties.choices import (
    ListingType,
    LocationPrecision,
    PropertyAssignmentCapability,
    PropertyAssignmentStatus,
    PropertyAssignmentType,
    PropertyStatus,
    PropertyType,
)
from apps.properties.models import Property, PropertyAssignment


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
def test_assigned_agent_with_manage_listing_can_retrieve_property_detail(
    api_client,
    other_user,
    property_listing,
):
    assign_manageable_property(property_listing, other_user)
    api_client.force_authenticate(other_user)

    response = api_client.get(reverse("properties-detail", args=[property_listing.slug]))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["id"] == str(property_listing.id)
    assert response.data["can_manage_listing"] is True


@pytest.mark.django_db
def test_assigned_agent_with_manage_listing_can_update_property(
    api_client,
    other_user,
    property_listing,
):
    property_listing.status = PropertyStatus.APPROVED
    property_listing.save(update_fields=["status"])
    assign_manageable_property(property_listing, other_user)
    api_client.force_authenticate(other_user)

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
@pytest.mark.parametrize(
    ("assignment_status", "expires_in_days", "capabilities"),
    [
        (PropertyAssignmentStatus.ACTIVE, None, [PropertyAssignmentCapability.MANAGE_LEADS]),
        (PropertyAssignmentStatus.REVOKED, None, [PropertyAssignmentCapability.MANAGE_LISTING]),
        (PropertyAssignmentStatus.SUSPENDED, None, [PropertyAssignmentCapability.MANAGE_LISTING]),
        (PropertyAssignmentStatus.ACTIVE, -1, [PropertyAssignmentCapability.MANAGE_LISTING]),
    ],
)
def test_agent_without_current_manage_listing_assignment_cannot_update_property(
    api_client,
    other_user,
    property_listing,
    assignment_status,
    expires_in_days,
    capabilities,
):
    expires_at = None
    if expires_in_days is not None:
        from django.utils import timezone

        expires_at = timezone.now() + timezone.timedelta(days=expires_in_days)
    assign_manageable_property(
        property_listing,
        other_user,
        status=assignment_status,
        expires_at=expires_at,
        capabilities=capabilities,
    )
    api_client.force_authenticate(other_user)

    response = api_client.patch(
        reverse("properties-detail", args=[property_listing.slug]),
        {"price": "125000000.00"},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_agent_manage_listing_assignment_does_not_allow_delete(
    api_client,
    other_user,
    property_listing,
):
    assign_manageable_property(property_listing, other_user)
    api_client.force_authenticate(other_user)

    response = api_client.delete(reverse("properties-detail", args=[property_listing.slug]))

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert Property.objects.filter(id=property_listing.id).exists()


def make_property(owner, title, status=PropertyStatus.DRAFT, **overrides):
    payload = {
        "owner": owner,
        "title": title,
        "description": f"{title} description.",
        "property_type": PropertyType.APARTMENT,
        "listing_type": ListingType.RENT,
        "price": "2500000.00",
        "currency": "NGN",
        "country": "Nigeria",
        "state": "Lagos",
        "city": "Lagos",
        "address": f"{title} address",
        "bedrooms": 2,
        "bathrooms": 2,
        "floor_area": "100.00",
        "status": status,
    }
    payload.update(overrides)
    return Property.objects.create(**payload)


def assign_manageable_property(prop, agent, **overrides):
    payload = {
        "property": prop,
        "user": agent,
        "relationship_type": PropertyAssignmentType.AGENT,
        "status": PropertyAssignmentStatus.ACTIVE,
        "capabilities": [PropertyAssignmentCapability.MANAGE_LISTING],
        "assigned_by": prop.owner,
    }
    payload.update(overrides)
    return PropertyAssignment.objects.create(**payload)


@pytest.mark.django_db
def test_mine_returns_landlord_owned_properties_by_status(api_client, user, other_user):
    draft = make_property(user, "Owner Draft", PropertyStatus.DRAFT)
    pending = make_property(user, "Owner Pending", PropertyStatus.PENDING_REVIEW)
    approved = make_property(user, "Owner Approved", PropertyStatus.APPROVED)
    rejected = make_property(user, "Owner Rejected", PropertyStatus.REJECTED)
    make_property(other_user, "Other Owner Approved", PropertyStatus.APPROVED)
    api_client.force_authenticate(user)

    response = api_client.get(reverse("properties-mine"))

    assert response.status_code == status.HTTP_200_OK
    returned_ids = {item["id"] for item in response.data["results"]}
    assert returned_ids == {str(draft.id), str(pending.id), str(approved.id), str(rejected.id)}


@pytest.mark.django_db
def test_properties_list_remains_owner_only_for_assigned_agent(api_client, user, other_user):
    assigned = make_property(other_user, "Assigned Managed Property", PropertyStatus.APPROVED)
    assign_manageable_property(assigned, user)
    api_client.force_authenticate(user)

    response = api_client.get(reverse("properties-list"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0


@pytest.mark.django_db
def test_mine_filters_status_search_and_ordering(api_client, user):
    make_property(user, "Zeta Draft", PropertyStatus.DRAFT)
    alpha = make_property(user, "Alpha Approved", PropertyStatus.APPROVED)
    beta = make_property(user, "Beta Approved", PropertyStatus.APPROVED)
    api_client.force_authenticate(user)

    response = api_client.get(
        reverse("properties-mine"),
        {"status": PropertyStatus.APPROVED, "search": "Approved", "ordering": "title"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert [item["id"] for item in response.data["results"]] == [str(alpha.id), str(beta.id)]


@pytest.mark.django_db
def test_mine_returns_agent_assigned_manageable_properties(api_client, user, other_user):
    owned = make_property(user, "Agent Owned Draft", PropertyStatus.DRAFT)
    assigned = make_property(other_user, "Assigned Managed Property", PropertyStatus.APPROVED)
    unassigned = make_property(other_user, "Unassigned Property", PropertyStatus.APPROVED)
    assign_manageable_property(assigned, user)
    api_client.force_authenticate(user)

    response = api_client.get(reverse("properties-mine"))

    assert response.status_code == status.HTTP_200_OK
    returned_ids = {item["id"] for item in response.data["results"]}
    assert returned_ids == {str(owned.id), str(assigned.id)}
    assert str(unassigned.id) not in returned_ids


@pytest.mark.django_db
def test_mine_excludes_assignments_without_manage_listing(api_client, user, other_user):
    prop = make_property(other_user, "Lead Only Assignment", PropertyStatus.APPROVED)
    assign_manageable_property(
        prop,
        user,
        capabilities=[PropertyAssignmentCapability.MANAGE_LEADS],
    )
    api_client.force_authenticate(user)

    response = api_client.get(reverse("properties-mine"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "assignment_status",
    [PropertyAssignmentStatus.REVOKED, PropertyAssignmentStatus.SUSPENDED],
)
def test_mine_excludes_inactive_assignments(api_client, user, other_user, assignment_status):
    prop = make_property(other_user, "Inactive Assignment", PropertyStatus.APPROVED)
    assign_manageable_property(prop, user, status=assignment_status)
    api_client.force_authenticate(user)

    response = api_client.get(reverse("properties-mine"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0


@pytest.mark.django_db
def test_mine_excludes_expired_assignments(api_client, user, other_user):
    from django.utils import timezone

    prop = make_property(other_user, "Expired Assignment", PropertyStatus.APPROVED)
    assign_manageable_property(prop, user, expires_at=timezone.now() - timezone.timedelta(days=1))
    api_client.force_authenticate(user)

    response = api_client.get(reverse("properties-mine"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0


@pytest.mark.django_db
def test_mine_deduplicates_owned_and_assigned_property(api_client, user):
    prop = make_property(user, "Owned And Assigned", PropertyStatus.APPROVED)
    assign_manageable_property(prop, user)
    api_client.force_authenticate(user)

    response = api_client.get(reverse("properties-mine"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(prop.id)


@pytest.mark.django_db
def test_mine_does_not_expose_unrelated_properties_to_buyer(api_client, user, other_user):
    make_property(other_user, "Another User Property", PropertyStatus.APPROVED)
    api_client.force_authenticate(user)

    response = api_client.get(reverse("properties-mine"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 0


@pytest.mark.django_db
def test_mine_preserves_admin_visibility(api_client, admin_user, user, other_user):
    first = make_property(user, "First Property", PropertyStatus.DRAFT)
    second = make_property(other_user, "Second Property", PropertyStatus.APPROVED)
    api_client.force_authenticate(admin_user)

    response = api_client.get(reverse("properties-mine"))

    assert response.status_code == status.HTTP_200_OK
    returned_ids = {item["id"] for item in response.data["results"]}
    assert {str(first.id), str(second.id)}.issubset(returned_ids)


@pytest.mark.django_db
def test_mine_uses_paginated_response(api_client, user):
    for index in range(21):
        make_property(user, f"Property {index:02d}", PropertyStatus.DRAFT)
    api_client.force_authenticate(user)

    response = api_client.get(reverse("properties-mine"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 21
    assert response.data["next"]
    assert response.data["previous"] is None
    assert len(response.data["results"]) == 20


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
def test_assigned_agent_with_manage_listing_can_submit_property_for_review(
    api_client,
    other_user,
    property_listing,
):
    property_listing.status = PropertyStatus.DRAFT
    property_listing.save(update_fields=["status"])
    assign_manageable_property(property_listing, other_user)
    api_client.force_authenticate(other_user)

    response = api_client.post(
        reverse("properties-submit-for-review", args=[property_listing.slug]),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    property_listing.refresh_from_db()
    assert property_listing.status == PropertyStatus.PENDING_REVIEW


@pytest.mark.django_db
def test_agent_without_manage_listing_cannot_submit_property_for_review(
    api_client,
    other_user,
    property_listing,
):
    property_listing.status = PropertyStatus.DRAFT
    property_listing.save(update_fields=["status"])
    assign_manageable_property(
        property_listing,
        other_user,
        capabilities=[PropertyAssignmentCapability.MANAGE_LEADS],
    )
    api_client.force_authenticate(other_user)

    response = api_client.post(
        reverse("properties-submit-for-review", args=[property_listing.slug]),
        {},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    property_listing.refresh_from_db()
    assert property_listing.status == PropertyStatus.DRAFT


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


@pytest.mark.django_db
def test_public_endpoint_filters_by_map_bounds(api_client, user):
    inside = Property.objects.create(
        owner=user,
        status=PropertyStatus.APPROVED,
        title="Lekki Map Apartment",
        description="Apartment with approved public map metadata.",
        property_type=PropertyType.APARTMENT,
        listing_type=ListingType.RENT,
        price="4500000.00",
        currency="NGN",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        lga="Eti-Osa",
        neighborhood="Lekki Phase 1",
        landmark="Admiralty Way",
        address="Admiralty Way, Lekki Phase 1",
        latitude="6.469800",
        longitude="3.585200",
        floor_area="180.00",
        bedrooms=3,
        bathrooms=3,
    )
    Property.objects.create(
        owner=user,
        status=PropertyStatus.APPROVED,
        title="Uyo Map Apartment",
        description="Apartment outside the Lagos viewport.",
        property_type=PropertyType.APARTMENT,
        listing_type=ListingType.RENT,
        price="1800000.00",
        currency="NGN",
        country="Nigeria",
        state="Akwa Ibom",
        city="Uyo",
        address="Shelter Afrique",
        latitude="5.037700",
        longitude="7.912800",
        floor_area="120.00",
        bedrooms=2,
        bathrooms=2,
    )

    response = api_client.get(
        reverse("public-properties-list"),
        {
            "min_lat": "6.0",
            "max_lat": "6.7",
            "min_lng": "3.0",
            "max_lng": "3.8",
            "has_map_location": "true",
        },
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(inside.id)


@pytest.mark.django_db
def test_public_endpoint_returns_approximate_location_metadata(api_client, property_listing):
    property_listing.latitude = "6.469812"
    property_listing.longitude = "3.585223"
    property_listing.location_precision = LocationPrecision.NEIGHBORHOOD
    property_listing.display_location = "Lekki Phase 1, Lagos"
    property_listing.address = "Private close off Admiralty Way"
    property_listing.save(
        update_fields=[
            "latitude",
            "longitude",
            "location_precision",
            "display_location",
            "address",
            "updated_at",
        ]
    )

    response = api_client.get(reverse("public-properties-detail", args=[property_listing.slug]))

    assert response.status_code == status.HTTP_200_OK
    assert str(response.data["latitude"]) == "6.470"
    assert str(response.data["longitude"]) == "3.585"
    assert response.data["address"] == "Lekki Phase 1, Lagos"
    assert response.data["approximate_location"] is True
    assert response.data["location_metadata"]["has_map_location"] is True


@pytest.mark.django_db
def test_public_endpoint_hides_hidden_location_coordinates(api_client, property_listing):
    property_listing.latitude = "6.469812"
    property_listing.longitude = "3.585223"
    property_listing.location_precision = LocationPrecision.HIDDEN
    property_listing.save(
        update_fields=["latitude", "longitude", "location_precision", "updated_at"]
    )

    response = api_client.get(reverse("public-properties-detail", args=[property_listing.slug]))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["latitude"] is None
    assert response.data["longitude"] is None
    assert response.data["location_metadata"]["has_map_location"] is False
