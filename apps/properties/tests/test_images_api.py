from unittest.mock import Mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status

from apps.properties.models import PropertyImage


@pytest.mark.django_db
def test_owner_can_upload_and_list_property_images(
    api_client,
    settings,
    tmp_path,
    user,
    property_listing,
    test_image_file,
):
    settings.MEDIA_ROOT = tmp_path
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("properties-images", args=[property_listing.slug]),
        {
            "image": test_image_file(),
            "caption": "Front elevation",
            "display_order": 1,
        },
        format="multipart",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["caption"] == "Front elevation"
    assert response.data["is_cover"] is True
    assert response.data["image_url"]

    list_response = api_client.get(reverse("properties-images", args=[property_listing.slug]))

    assert list_response.status_code == status.HTTP_200_OK
    assert len(list_response.data) == 1
    assert list_response.data[0]["caption"] == "Front elevation"


@pytest.mark.django_db
def test_admin_can_manage_any_property_images(
    api_client,
    settings,
    tmp_path,
    admin_user,
    property_listing,
    test_image_file,
):
    settings.MEDIA_ROOT = tmp_path
    api_client.force_authenticate(admin_user)

    response = api_client.post(
        reverse("properties-images", args=[property_listing.slug]),
        {"image": test_image_file("admin.jpg")},
        format="multipart",
    )

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_non_owner_cannot_manage_property_images(
    api_client,
    other_user,
    property_listing,
    test_image_file,
):
    api_client.force_authenticate(other_user)

    response = api_client.post(
        reverse("properties-images", args=[property_listing.slug]),
        {"image": test_image_file()},
        format="multipart",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_update_image_metadata_and_set_cover(
    api_client,
    settings,
    tmp_path,
    user,
    property_listing,
    test_image_file,
):
    settings.MEDIA_ROOT = tmp_path
    first = PropertyImage.objects.create(
        property=property_listing,
        image=test_image_file("first.jpg"),
        is_cover=True,
    )
    second = PropertyImage.objects.create(
        property=property_listing,
        image=test_image_file("second.jpg"),
        display_order=2,
    )
    api_client.force_authenticate(user)

    metadata_response = api_client.patch(
        reverse("properties-image-detail", args=[property_listing.slug, second.id]),
        {"caption": "Kitchen", "display_order": 1},
        format="json",
    )
    cover_response = api_client.post(
        reverse("properties-set-cover-image", args=[property_listing.slug, second.id]),
        {},
        format="json",
    )

    assert metadata_response.status_code == status.HTTP_200_OK
    assert metadata_response.data["caption"] == "Kitchen"
    assert cover_response.status_code == status.HTTP_200_OK
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_cover is False
    assert second.is_cover is True


@pytest.mark.django_db
def test_delete_image_removes_record_and_promotes_replacement_cover(
    api_client,
    settings,
    tmp_path,
    user,
    property_listing,
    test_image_file,
    monkeypatch,
):
    settings.MEDIA_ROOT = tmp_path
    first = PropertyImage.objects.create(
        property=property_listing,
        image=test_image_file("first.jpg"),
        is_cover=True,
    )
    replacement = PropertyImage.objects.create(
        property=property_listing,
        image=test_image_file("replacement.jpg"),
        display_order=2,
    )
    delete_file = Mock()
    monkeypatch.setattr(first.image, "delete", delete_file)
    api_client.force_authenticate(user)

    response = api_client.delete(
        reverse("properties-image-detail", args=[property_listing.slug, first.id])
    )

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not PropertyImage.objects.filter(id=first.id).exists()
    replacement.refresh_from_db()
    assert replacement.is_cover is True


@pytest.mark.django_db
def test_upload_rejects_invalid_image_type(
    api_client,
    settings,
    tmp_path,
    user,
    property_listing,
):
    settings.MEDIA_ROOT = tmp_path
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("properties-images", args=[property_listing.slug]),
        {
            "image": SimpleUploadedFile(
                "notes.txt",
                b"not an image",
                content_type="text/plain",
            )
        },
        format="multipart",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "image" in response.data


@pytest.mark.django_db
def test_upload_rejects_large_images(
    api_client,
    settings,
    tmp_path,
    user,
    property_listing,
    test_image_file,
):
    settings.MEDIA_ROOT = tmp_path
    settings.PROPERTY_IMAGE_MAX_SIZE_MB = 0
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("properties-images", args=[property_listing.slug]),
        {"image": test_image_file()},
        format="multipart",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "image" in response.data


@pytest.mark.django_db
def test_upload_rejects_more_than_max_images(
    api_client,
    settings,
    tmp_path,
    user,
    property_listing,
    test_image_file,
):
    settings.MEDIA_ROOT = tmp_path
    settings.PROPERTY_IMAGE_MAX_COUNT = 1
    PropertyImage.objects.create(property=property_listing, image=test_image_file("existing.jpg"))
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("properties-images", args=[property_listing.slug]),
        {"image": test_image_file("new.jpg")},
        format="multipart",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "image" in response.data


@pytest.mark.django_db
def test_public_property_response_includes_gallery(
    api_client,
    settings,
    tmp_path,
    property_listing,
    test_image_file,
):
    settings.MEDIA_ROOT = tmp_path
    PropertyImage.objects.create(
        property=property_listing,
        image=test_image_file("cover.jpg"),
        caption="Cover",
        is_cover=True,
    )
    PropertyImage.objects.create(
        property=property_listing,
        image=test_image_file("gallery.jpg"),
        caption="Gallery",
        display_order=2,
    )

    response = api_client.get(reverse("public-properties-detail", args=[property_listing.slug]))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["cover_image_url"]
    assert response.data["image_count"] == 2
    assert len(response.data["image_gallery"]) == 2
