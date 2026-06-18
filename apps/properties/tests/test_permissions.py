import pytest
from rest_framework.test import APIRequestFactory

from apps.properties.permissions import IsOwnerOrAdmin


@pytest.mark.django_db
def test_owner_can_modify_property(user, property_listing):
    request = APIRequestFactory().patch("/")
    request.user = user

    assert IsOwnerOrAdmin().has_object_permission(request, None, property_listing)


@pytest.mark.django_db
def test_admin_can_modify_any_property(admin_user, property_listing):
    request = APIRequestFactory().patch("/")
    request.user = admin_user

    assert IsOwnerOrAdmin().has_object_permission(request, None, property_listing)


@pytest.mark.django_db
def test_non_owner_cannot_modify_property(other_user, property_listing):
    request = APIRequestFactory().patch("/")
    request.user = other_user

    assert not IsOwnerOrAdmin().has_object_permission(request, None, property_listing)
