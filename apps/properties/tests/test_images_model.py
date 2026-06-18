import pytest

from apps.properties.models import PropertyImage


@pytest.mark.django_db
def test_property_image_cover_is_unique(settings, tmp_path, property_listing, test_image_file):
    settings.MEDIA_ROOT = tmp_path
    first = PropertyImage.objects.create(
        property=property_listing,
        image=test_image_file("first.jpg"),
        is_cover=True,
    )
    second = PropertyImage.objects.create(
        property=property_listing,
        image=test_image_file("second.jpg"),
        is_cover=True,
    )

    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_cover is False
    assert second.is_cover is True


@pytest.mark.django_db
def test_property_image_ordering(settings, tmp_path, property_listing, test_image_file):
    settings.MEDIA_ROOT = tmp_path
    second = PropertyImage.objects.create(
        property=property_listing,
        image=test_image_file("second.jpg"),
        display_order=2,
    )
    first = PropertyImage.objects.create(
        property=property_listing,
        image=test_image_file("first.jpg"),
        display_order=1,
    )

    assert list(property_listing.images.all()) == [first, second]
