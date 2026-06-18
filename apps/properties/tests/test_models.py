from decimal import Decimal

import pytest

from apps.properties.choices import PropertyStatus, PropertyType
from apps.properties.models import Property


@pytest.mark.django_db
def test_property_generates_unique_slug(user, property_payload):
    first = Property.objects.create(owner=user, **property_payload)
    second = Property.objects.create(owner=user, **property_payload)

    assert first.slug == "modern-lekki-apartment"
    assert second.slug == "modern-lekki-apartment-2"


@pytest.mark.django_db
def test_property_workflow_status_helpers(property_listing):
    property_listing.status = PropertyStatus.DRAFT
    property_listing.save(update_fields=["status"])

    property_listing.submit_for_review()
    assert property_listing.status == PropertyStatus.PENDING_REVIEW

    property_listing.approve()
    assert property_listing.status == PropertyStatus.APPROVED

    property_listing.reject()
    assert property_listing.status == PropertyStatus.REJECTED


@pytest.mark.django_db
def test_property_soft_delete_removes_from_default_queryset(property_listing):
    property_id = property_listing.id

    property_listing.delete()

    assert not Property.objects.filter(id=property_id).exists()
    assert Property.all_objects.filter(id=property_id, deleted_at__isnull=False).exists()


@pytest.mark.django_db
def test_land_property_flag(user, property_payload):
    property_payload["property_type"] = PropertyType.LAND
    property_payload["land_size"] = Decimal("650.00")
    property_payload.pop("floor_area")

    prop = Property.objects.create(owner=user, **property_payload)

    assert prop.is_land is True
