from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.properties.choices import InquiryType, RentalApplicationStatus, ViewingStatus, ViewingType
from apps.properties.models import Inquiry, RentalApplication, Viewing


@pytest.fixture
def workflow_records(property_listing, other_user):
    inquiry = Inquiry.objects.create(
        property=property_listing,
        interested_user=other_user,
        property_owner=property_listing.owner,
        inquiry_type=InquiryType.PURCHASE,
    )
    viewing = Viewing.objects.create(
        inquiry=inquiry,
        property=property_listing,
        requester=other_user,
        property_owner=property_listing.owner,
        viewing_type=ViewingType.PHYSICAL,
        preferred_date=timezone.localdate() + timedelta(days=3),
        preferred_time="14:00:00",
        confirmed_datetime=timezone.now() + timedelta(days=3),
        status=ViewingStatus.COMPLETED,
    )
    application = RentalApplication.objects.create(
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
        status=RentalApplicationStatus.UNDER_REVIEW,
    )
    return inquiry, viewing, application


@pytest.mark.django_db
def test_transaction_center_returns_current_stage(api_client, workflow_records, other_user):
    inquiry, viewing, application = workflow_records
    api_client.force_authenticate(other_user)

    response = api_client.get(reverse("dashboard-transactions"))

    assert response.status_code == 200
    assert response.data[0]["property"]["id"] == str(inquiry.property_id)
    assert response.data[0]["stage"] == RentalApplicationStatus.UNDER_REVIEW
    assert response.data[0]["stage_label"] == "Application Under Review"
    assert response.data[0]["inquiry_id"] == str(inquiry.id)
    assert response.data[0]["viewing_id"] == str(viewing.id)
    assert response.data[0]["application_id"] == str(application.id)


@pytest.mark.django_db
def test_dashboard_activity_feed_returns_relevant_events(
    api_client,
    workflow_records,
    other_user,
):
    _, _, application = workflow_records
    AuditLog.objects.create(
        actor=other_user,
        action="application.submitted",
        entity_type="RentalApplication",
        entity_id=application.id,
        metadata={
            "property_id": str(application.property_id),
            "applicant_id": str(other_user.id),
            "property_owner_id": str(application.property_owner_id),
        },
    )
    api_client.force_authenticate(other_user)

    response = api_client.get(reverse("dashboard-activity"))

    assert response.status_code == 200
    assert response.data[0]["action"] == "application.submitted"
    assert response.data[0]["label"] == "Application submitted"
    assert response.data[0]["property_id"] == str(application.property_id)
