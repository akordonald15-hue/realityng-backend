import pytest

from apps.services.serializers import PublicServiceProviderDetailSerializer


@pytest.mark.django_db
def test_public_provider_serializer_excludes_private_address(active_provider):
    data = PublicServiceProviderDetailSerializer(active_provider).data

    assert data["display_location"] == "Lekki, Lagos"
    assert "private_address" not in data
    assert "verification_snapshot" not in data
    assert data["verification_badges"][0]["label"] == "Identity Verified"
    assert data["portfolio"]["items"] == []
    assert data["reviews_summary"]["review_count"] == 0
