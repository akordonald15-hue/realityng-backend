import pytest
from django.urls import reverse

from apps.accounts.models import AuditLog
from apps.properties.choices import InquiryStatus, InquiryType
from apps.properties.models import Inquiry


@pytest.mark.django_db
def test_authenticated_user_can_create_inquiry(api_client, property_listing, other_user):
    api_client.force_authenticate(other_user)

    response = api_client.post(
        reverse("inquiries-list"),
        {
            "property_id": str(property_listing.id),
            "inquiry_type": InquiryType.PURCHASE,
            "message": "I would like to discuss this property.",
            "contact_preference": "whatsapp",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["status"] == InquiryStatus.NEW
    assert response.data["property"]["id"] == str(property_listing.id)
    assert response.data["property_owner"]["email"] == property_listing.owner.email
    assert response.data["interested_user"]["email"] == other_user.email
    assert Inquiry.objects.filter(property=property_listing, interested_user=other_user).exists()
    assert AuditLog.objects.filter(action="inquiry.created").exists()


@pytest.mark.django_db
def test_anonymous_user_cannot_create_inquiry(api_client, property_listing):
    response = api_client.post(
        reverse("inquiries-list"),
        {
            "property_id": str(property_listing.id),
            "inquiry_type": InquiryType.PURCHASE,
            "contact_preference": "email",
        },
        format="json",
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_owner_cannot_create_inquiry_for_own_property(api_client, property_listing, user):
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("inquiries-list"),
        {
            "property_id": str(property_listing.id),
            "inquiry_type": InquiryType.PURCHASE,
            "contact_preference": "email",
        },
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_inquiry_type_must_match_listing_type(api_client, property_listing, other_user):
    api_client.force_authenticate(other_user)

    response = api_client.post(
        reverse("inquiries-list"),
        {
            "property_id": str(property_listing.id),
            "inquiry_type": InquiryType.RENT,
            "contact_preference": "email",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "inquiry_type" in response.data


@pytest.mark.django_db
def test_interested_user_lists_their_inquiries(api_client, property_listing, other_user):
    inquiry = Inquiry.objects.create(
        property=property_listing,
        interested_user=other_user,
        property_owner=property_listing.owner,
        inquiry_type=InquiryType.PURCHASE,
    )
    api_client.force_authenticate(other_user)

    response = api_client.get(reverse("inquiries-list"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(inquiry.id)


@pytest.mark.django_db
def test_owner_lists_received_inquiries(api_client, property_listing, other_user, user):
    inquiry = Inquiry.objects.create(
        property=property_listing,
        interested_user=other_user,
        property_owner=user,
        inquiry_type=InquiryType.PURCHASE,
    )
    api_client.force_authenticate(user)

    response = api_client.get(reverse("inquiries-received"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(inquiry.id)


@pytest.mark.django_db
def test_only_owner_can_update_status(api_client, property_listing, other_user, user):
    inquiry = Inquiry.objects.create(
        property=property_listing,
        interested_user=other_user,
        property_owner=user,
        inquiry_type=InquiryType.PURCHASE,
    )

    api_client.force_authenticate(other_user)
    forbidden = api_client.post(
        reverse("inquiries-update-status", kwargs={"pk": inquiry.id}),
        {"status": InquiryStatus.CONTACTED},
        format="json",
    )
    assert forbidden.status_code == 403

    api_client.force_authenticate(user)
    response = api_client.post(
        reverse("inquiries-update-status", kwargs={"pk": inquiry.id}),
        {"status": InquiryStatus.CONTACTED},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["status"] == InquiryStatus.CONTACTED
    assert AuditLog.objects.filter(action="inquiry.status_changed").exists()


@pytest.mark.django_db
def test_invalid_status_transition_is_rejected(api_client, property_listing, other_user, user):
    inquiry = Inquiry.objects.create(
        property=property_listing,
        interested_user=other_user,
        property_owner=user,
        inquiry_type=InquiryType.PURCHASE,
    )
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("inquiries-update-status", kwargs={"pk": inquiry.id}),
        {"status": InquiryStatus.CONVERTED},
        format="json",
    )

    assert response.status_code == 400
    inquiry.refresh_from_db()
    assert inquiry.status == InquiryStatus.NEW


@pytest.mark.django_db
def test_owner_notes_are_private_to_owner(api_client, property_listing, other_user, user):
    inquiry = Inquiry.objects.create(
        property=property_listing,
        interested_user=other_user,
        property_owner=user,
        inquiry_type=InquiryType.PURCHASE,
    )

    api_client.force_authenticate(user)
    response = api_client.patch(
        reverse("inquiries-update-notes", kwargs={"pk": inquiry.id}),
        {"internal_notes": "Call after 4pm."},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["internal_notes"] == "Call after 4pm."
    assert AuditLog.objects.filter(action="inquiry.updated").exists()

    api_client.force_authenticate(other_user)
    response = api_client.get(reverse("inquiries-detail", kwargs={"pk": inquiry.id}))

    assert response.status_code == 200
    assert response.data["internal_notes"] == ""
