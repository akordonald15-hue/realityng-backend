import pytest
from rest_framework.test import APIRequestFactory

from apps.properties.choices import ListingType, PropertyStatus, PropertyType
from apps.properties.serializers import PropertySerializer


@pytest.mark.django_db
def test_serializer_rejects_non_positive_price(user, property_payload):
    property_payload["price"] = "0"
    request = APIRequestFactory().post("/")
    request.user = user

    serializer = PropertySerializer(data=property_payload, context={"request": request})

    assert not serializer.is_valid()
    assert "price" in serializer.errors


@pytest.mark.django_db
def test_serializer_requires_location_fields(user, property_payload):
    property_payload["city"] = ""
    request = APIRequestFactory().post("/")
    request.user = user

    serializer = PropertySerializer(data=property_payload, context={"request": request})

    assert not serializer.is_valid()
    assert "city" in serializer.errors


@pytest.mark.django_db
def test_serializer_requires_land_size_for_land(user, property_payload):
    property_payload["property_type"] = PropertyType.LAND
    property_payload.pop("floor_area")
    request = APIRequestFactory().post("/")
    request.user = user

    serializer = PropertySerializer(data=property_payload, context={"request": request})

    assert not serializer.is_valid()
    assert "land_size" in serializer.errors


@pytest.mark.django_db
def test_serializer_accepts_apartment_share_for_apartment(user, property_payload):
    property_payload["property_type"] = PropertyType.APARTMENT
    property_payload["listing_type"] = ListingType.APARTMENT_SHARE
    request = APIRequestFactory().post("/")
    request.user = user

    serializer = PropertySerializer(data=property_payload, context={"request": request})

    assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
def test_serializer_rejects_apartment_share_for_non_apartment(user, property_payload):
    property_payload["property_type"] = PropertyType.HOUSE
    property_payload["listing_type"] = ListingType.APARTMENT_SHARE
    request = APIRequestFactory().post("/")
    request.user = user

    serializer = PropertySerializer(data=property_payload, context={"request": request})

    assert not serializer.is_valid()
    assert "property_type" in serializer.errors


@pytest.mark.django_db
def test_serializer_sets_owner_and_draft_status(user, property_payload):
    request = APIRequestFactory().post("/")
    request.user = user

    serializer = PropertySerializer(data=property_payload, context={"request": request})
    assert serializer.is_valid(), serializer.errors
    prop = serializer.save()

    assert prop.owner == user
    assert prop.status == PropertyStatus.DRAFT
