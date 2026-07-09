from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.properties.choices import (
    InquiryType,
    RentalApplicationStatus,
    ViewingStatus,
    ViewingType,
)
from apps.properties.models import Inquiry, RentalApplication, Viewing


@pytest.fixture
def inquiry(property_listing, other_user):
    return Inquiry.objects.create(
        property=property_listing,
        interested_user=other_user,
        property_owner=property_listing.owner,
        inquiry_type=InquiryType.PURCHASE,
    )


@pytest.fixture
def viewing(inquiry):
    return Viewing.objects.create(
        inquiry=inquiry,
        property=inquiry.property,
        requester=inquiry.interested_user,
        property_owner=inquiry.property_owner,
        viewing_type=ViewingType.PHYSICAL,
        preferred_date=timezone.localdate() + timedelta(days=3),
        preferred_time="14:00:00",
        confirmed_datetime=timezone.now() + timedelta(days=3),
        status=ViewingStatus.COMPLETED,
    )


@pytest.fixture
def application(property_listing, other_user, inquiry, viewing):
    return RentalApplication.objects.create(
        property=property_listing,
        applicant=other_user,
        property_owner=property_listing.owner,
        inquiry=inquiry,
        viewing=viewing,
        full_name="Ada Okoro",
        email="ada@example.com",
        phone="+2348012345678",
        employment_status="Employed",
        employer_name="RealityNG Demo Holdings",
        monthly_income="850000.00",
        move_in_date=timezone.localdate() + timedelta(days=30),
        message="I am ready to move in after verification.",
    )


def application_payload(property_listing, inquiry=None, viewing=None):
    payload = {
        "property_id": str(property_listing.id),
        "full_name": "Ada Okoro",
        "email": "ada@example.com",
        "phone": "+2348012345678",
        "employment_status": "Employed",
        "employer_name": "RealityNG Demo Holdings",
        "monthly_income": "850000.00",
        "move_in_date": str(timezone.localdate() + timedelta(days=30)),
        "message": "I am ready to move in after verification.",
    }
    if inquiry:
        payload["inquiry_id"] = str(inquiry.id)
    if viewing:
        payload["viewing_id"] = str(viewing.id)
    return payload


@pytest.mark.django_db
def test_authenticated_user_can_submit_application(api_client, property_listing, other_user):
    api_client.force_authenticate(other_user)

    response = api_client.post(
        reverse("applications-list"),
        application_payload(property_listing),
        format="json",
    )

    assert response.status_code == 201
    assert response.data["status"] == RentalApplicationStatus.SUBMITTED
    assert response.data["property"]["id"] == str(property_listing.id)
    assert response.data["applicant"]["email"] == other_user.email
    assert RentalApplication.objects.filter(applicant=other_user).exists()
    assert AuditLog.objects.filter(action="application.submitted").exists()


@pytest.mark.django_db
def test_application_can_link_completed_viewing(
    api_client,
    property_listing,
    other_user,
    inquiry,
    viewing,
):
    api_client.force_authenticate(other_user)

    response = api_client.post(
        reverse("applications-list"),
        application_payload(property_listing, inquiry=inquiry, viewing=viewing),
        format="json",
    )

    assert response.status_code == 201
    assert response.data["inquiry"] == str(inquiry.id)
    assert response.data["viewing"] == str(viewing.id)


@pytest.mark.django_db
def test_owner_cannot_apply_for_own_property(api_client, property_listing, user):
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("applications-list"),
        application_payload(property_listing),
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_applicant_lists_their_applications(api_client, application, other_user):
    api_client.force_authenticate(other_user)

    response = api_client.get(reverse("applications-list"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(application.id)
    assert response.data["results"][0]["owner_notes"] == ""


@pytest.mark.django_db
def test_owner_lists_received_applications(api_client, application, user):
    api_client.force_authenticate(user)

    response = api_client.get(reverse("applications-received"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(application.id)


@pytest.mark.django_db
def test_only_owner_can_mark_application_under_review(api_client, application, other_user, user):
    api_client.force_authenticate(other_user)
    forbidden = api_client.post(
        reverse("applications-mark-under-review", kwargs={"pk": application.id})
    )
    assert forbidden.status_code == 403

    api_client.force_authenticate(user)
    response = api_client.post(
        reverse("applications-mark-under-review", kwargs={"pk": application.id})
    )

    assert response.status_code == 200
    assert response.data["status"] == RentalApplicationStatus.UNDER_REVIEW
    assert AuditLog.objects.filter(action="application.under_review").exists()


@pytest.mark.django_db
def test_owner_can_approve_under_review_application(api_client, application, user):
    application.status = RentalApplicationStatus.UNDER_REVIEW
    application.save(update_fields=["status", "updated_at"])
    api_client.force_authenticate(user)

    response = api_client.post(reverse("applications-approve", kwargs={"pk": application.id}))

    assert response.status_code == 200
    assert response.data["status"] == RentalApplicationStatus.APPROVED
    assert AuditLog.objects.filter(action="application.approved").exists()


@pytest.mark.django_db
def test_owner_can_reject_under_review_application(api_client, application, user):
    application.status = RentalApplicationStatus.UNDER_REVIEW
    application.save(update_fields=["status", "updated_at"])
    api_client.force_authenticate(user)

    response = api_client.post(reverse("applications-reject", kwargs={"pk": application.id}))

    assert response.status_code == 200
    assert response.data["status"] == RentalApplicationStatus.REJECTED
    assert AuditLog.objects.filter(action="application.rejected").exists()


@pytest.mark.django_db
def test_direct_approval_from_submitted_is_rejected(api_client, application, user):
    api_client.force_authenticate(user)

    response = api_client.post(reverse("applications-approve", kwargs={"pk": application.id}))

    assert response.status_code == 400
    application.refresh_from_db()
    assert application.status == RentalApplicationStatus.SUBMITTED


@pytest.mark.django_db
def test_applicant_can_withdraw_application(api_client, application, other_user):
    api_client.force_authenticate(other_user)

    response = api_client.post(reverse("applications-withdraw", kwargs={"pk": application.id}))

    assert response.status_code == 200
    assert response.data["status"] == RentalApplicationStatus.WITHDRAWN
    assert AuditLog.objects.filter(action="application.withdrawn").exists()


@pytest.mark.django_db
def test_owner_notes_are_private_to_owner(api_client, application, user, other_user):
    api_client.force_authenticate(other_user)
    forbidden = api_client.patch(
        reverse("applications-update-notes", kwargs={"pk": application.id}),
        {"owner_notes": "Strong applicant."},
        format="json",
    )
    assert forbidden.status_code == 403

    api_client.force_authenticate(user)
    response = api_client.patch(
        reverse("applications-update-notes", kwargs={"pk": application.id}),
        {"owner_notes": "Strong applicant."},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["owner_notes"] == "Strong applicant."

    api_client.force_authenticate(other_user)
    applicant_view = api_client.get(reverse("applications-detail", kwargs={"pk": application.id}))
    assert applicant_view.status_code == 200
    assert applicant_view.data["owner_notes"] == ""


@pytest.mark.django_db
def test_admin_can_manage_application(api_client, application, admin_user):
    application.status = RentalApplicationStatus.UNDER_REVIEW
    application.save(update_fields=["status", "updated_at"])
    api_client.force_authenticate(admin_user)

    response = api_client.post(reverse("applications-approve", kwargs={"pk": application.id}))

    assert response.status_code == 200
    assert response.data["status"] == RentalApplicationStatus.APPROVED
