from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AuditLog, User
from apps.properties.choices import (
    InquiryType,
    PropertyAssignmentCapability,
    PropertyAssignmentStatus,
    PropertyAssignmentType,
    RentalApplicationStatus,
    ViewingStatus,
    ViewingType,
)
from apps.properties.models import Inquiry, PropertyAssignment, RentalApplication, Viewing


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


def assign_application_manager(prop, agent, **overrides):
    payload = {
        "property": prop,
        "user": agent,
        "relationship_type": PropertyAssignmentType.AGENT,
        "status": PropertyAssignmentStatus.ACTIVE,
        "capabilities": [PropertyAssignmentCapability.MANAGE_APPLICATIONS],
        "assigned_by": prop.owner,
    }
    payload.update(overrides)
    return PropertyAssignment.objects.create(**payload)


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
def test_applicant_can_retrieve_own_application_detail(api_client, application, other_user):
    api_client.force_authenticate(other_user)

    response = api_client.get(reverse("applications-detail", kwargs={"pk": application.id}))

    assert response.status_code == 200
    assert response.data["id"] == str(application.id)
    assert response.data["property"]["id"] == str(application.property_id)
    assert response.data["property"]["title"] == application.property.title
    assert response.data["property"]["price"] == str(application.property.price)
    assert response.data["property"]["currency"] == application.property.currency
    assert response.data["property"]["listing_type"] == application.property.listing_type
    assert response.data["property"]["property_type"] == application.property.property_type
    assert response.data["property"]["city"] == application.property.city
    assert response.data["property"]["state"] == application.property.state
    assert response.data["applicant"]["id"] == str(other_user.id)
    assert response.data["property_owner"]["id"] == str(application.property_owner_id)
    assert response.data["inquiry"] == str(application.inquiry_id)
    assert response.data["viewing"] == str(application.viewing_id)
    assert response.data["full_name"] == application.full_name
    assert response.data["email"] == application.email
    assert response.data["phone"] == application.phone
    assert response.data["employment_status"] == application.employment_status
    assert response.data["employer_name"] == application.employer_name
    assert response.data["monthly_income"] == str(application.monthly_income)
    assert response.data["move_in_date"] == str(application.move_in_date)
    assert response.data["message"] == application.message
    assert response.data["status"] == RentalApplicationStatus.SUBMITTED
    assert response.data["owner_notes"] == ""
    assert "created_at" in response.data
    assert "updated_at" in response.data


@pytest.mark.django_db
def test_unrelated_customer_cannot_retrieve_application_detail(api_client, application):
    unrelated_customer = User.objects.create_user(
        email="unrelated@example.com",
        password="Str0ngPass123!",
    )
    api_client.force_authenticate(unrelated_customer)

    response = api_client.get(reverse("applications-detail", kwargs={"pk": application.id}))

    assert response.status_code == 404


@pytest.mark.django_db
def test_owner_and_admin_can_retrieve_application_detail(
    api_client, application, user, admin_user
):
    application.owner_notes = "Strong applicant."
    application.save(update_fields=["owner_notes", "updated_at"])

    api_client.force_authenticate(user)
    owner_response = api_client.get(reverse("applications-detail", kwargs={"pk": application.id}))
    assert owner_response.status_code == 200
    assert owner_response.data["owner_notes"] == "Strong applicant."
    assert owner_response.data["can_manage_application"] is True

    api_client.force_authenticate(admin_user)
    admin_response = api_client.get(reverse("applications-detail", kwargs={"pk": application.id}))
    assert admin_response.status_code == 200
    assert admin_response.data["id"] == str(application.id)
    assert admin_response.data["owner_notes"] == "Strong applicant."
    assert admin_response.data["can_manage_application"] is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "application_status",
    [
        RentalApplicationStatus.SUBMITTED,
        RentalApplicationStatus.UNDER_REVIEW,
        RentalApplicationStatus.APPROVED,
        RentalApplicationStatus.REJECTED,
        RentalApplicationStatus.WITHDRAWN,
    ],
)
def test_application_detail_returns_all_supported_statuses(
    api_client, application, other_user, application_status
):
    application.status = application_status
    application.save(update_fields=["status", "updated_at"])
    api_client.force_authenticate(other_user)

    response = api_client.get(reverse("applications-detail", kwargs={"pk": application.id}))

    assert response.status_code == 200
    assert response.data["status"] == application_status


@pytest.mark.django_db
def test_owner_lists_received_applications(api_client, application, user):
    api_client.force_authenticate(user)

    response = api_client.get(reverse("applications-received"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(application.id)
    assert response.data["results"][0]["can_manage_application"] is True


@pytest.mark.django_db
def test_assigned_agent_with_manage_applications_lists_and_retrieves_received_application(
    api_client, application
):
    agent = User.objects.create_user(
        email="application-agent@example.com",
        password="Str0ngPass123!",
    )
    assign_application_manager(application.property, agent)
    application.owner_notes = "Delegated application note."
    application.save(update_fields=["owner_notes", "updated_at"])
    api_client.force_authenticate(agent)

    list_response = api_client.get(reverse("applications-received"))
    detail_response = api_client.get(reverse("applications-detail", kwargs={"pk": application.id}))

    assert list_response.status_code == 200
    assert list_response.data["count"] == 1
    assert list_response.data["results"][0]["id"] == str(application.id)
    assert list_response.data["results"][0]["owner_notes"] == "Delegated application note."
    assert list_response.data["results"][0]["can_manage_application"] is True
    assert detail_response.status_code == 200
    assert detail_response.data["id"] == str(application.id)
    assert detail_response.data["owner_notes"] == "Delegated application note."
    assert detail_response.data["can_manage_application"] is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("assignment_status", "expires_in_days", "capabilities"),
    [
        (
            PropertyAssignmentStatus.ACTIVE,
            None,
            [PropertyAssignmentCapability.MANAGE_LEADS],
        ),
        (
            PropertyAssignmentStatus.REVOKED,
            None,
            [PropertyAssignmentCapability.MANAGE_APPLICATIONS],
        ),
        (
            PropertyAssignmentStatus.SUSPENDED,
            None,
            [PropertyAssignmentCapability.MANAGE_APPLICATIONS],
        ),
        (
            PropertyAssignmentStatus.ACTIVE,
            -1,
            [PropertyAssignmentCapability.MANAGE_APPLICATIONS],
        ),
    ],
)
def test_agent_without_current_manage_applications_assignment_cannot_access_received_application(
    api_client,
    application,
    assignment_status,
    expires_in_days,
    capabilities,
):
    agent = User.objects.create_user(
        email=f"application-agent-{assignment_status}-{expires_in_days}@example.com",
        password="Str0ngPass123!",
    )
    expires_at = None
    if expires_in_days is not None:
        expires_at = timezone.now() + timedelta(days=expires_in_days)
    assign_application_manager(
        application.property,
        agent,
        status=assignment_status,
        expires_at=expires_at,
        capabilities=capabilities,
    )
    api_client.force_authenticate(agent)

    list_response = api_client.get(reverse("applications-received"))
    detail_response = api_client.get(reverse("applications-detail", kwargs={"pk": application.id}))

    assert list_response.status_code == 200
    assert list_response.data["count"] == 0
    assert detail_response.status_code == 404


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
def test_assigned_agent_with_manage_applications_can_decide_and_update_notes(
    api_client, application
):
    agent = User.objects.create_user(email="decision-agent@example.com", password="Str0ngPass123!")
    assign_application_manager(application.property, agent)
    api_client.force_authenticate(agent)

    under_review = api_client.post(
        reverse("applications-mark-under-review", kwargs={"pk": application.id})
    )
    notes = api_client.patch(
        reverse("applications-update-notes", kwargs={"pk": application.id}),
        {"owner_notes": "Agent-reviewed application."},
        format="json",
    )
    approved = api_client.post(reverse("applications-approve", kwargs={"pk": application.id}))

    assert under_review.status_code == 200
    assert under_review.data["status"] == RentalApplicationStatus.UNDER_REVIEW
    assert notes.status_code == 200
    assert notes.data["owner_notes"] == "Agent-reviewed application."
    assert approved.status_code == 200
    assert approved.data["status"] == RentalApplicationStatus.APPROVED


@pytest.mark.django_db
def test_assigned_agent_without_manage_applications_cannot_decide_or_update_notes(
    api_client, application
):
    agent = User.objects.create_user(email="lead-only-agent@example.com", password="Str0ngPass123!")
    assign_application_manager(
        application.property,
        agent,
        capabilities=[PropertyAssignmentCapability.MANAGE_LEADS],
    )
    api_client.force_authenticate(agent)

    under_review = api_client.post(
        reverse("applications-mark-under-review", kwargs={"pk": application.id})
    )
    notes = api_client.patch(
        reverse("applications-update-notes", kwargs={"pk": application.id}),
        {"owner_notes": "Should not save."},
        format="json",
    )

    assert under_review.status_code == 404
    assert notes.status_code == 404


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
