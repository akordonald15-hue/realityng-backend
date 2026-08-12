import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.properties.choices import (
    InquiryType,
    LeadActivityType,
    LeadPipelineStage,
    PropertyAssignmentCapability,
    PropertyAssignmentStatus,
    PropertyAssignmentType,
)
from apps.properties.models import Inquiry, PropertyAssignment


@pytest.fixture
def lead(property_listing, other_user, user):
    return Inquiry.objects.create(
        property=property_listing,
        interested_user=other_user,
        property_owner=user,
        inquiry_type=InquiryType.PURCHASE,
        internal_notes="Buyer prefers evening calls.",
    )


@pytest.fixture
def agent(db):
    from apps.accounts.models import User

    return User.objects.create_user(
        email="assigned-agent@example.com",
        password="Str0ngPass123!",
        first_name="Assigned",
    )


def assign_property(property_listing, agent, status=PropertyAssignmentStatus.ACTIVE):
    return PropertyAssignment.objects.create(
        property=property_listing,
        user=agent,
        relationship_type=PropertyAssignmentType.AGENT,
        status=status,
        capabilities=[PropertyAssignmentCapability.MANAGE_LEADS],
    )


@pytest.mark.django_db
def test_owner_can_view_lead_with_internal_fields(api_client, lead, user):
    api_client.force_authenticate(user)

    response = api_client.get(reverse("leads-detail", args=[lead.id]))

    assert response.status_code == 200
    assert response.data["id"] == str(lead.id)
    assert response.data["internal_notes"] == "Buyer prefers evening calls."


@pytest.mark.django_db
def test_buyer_cannot_access_internal_lead_endpoint(api_client, lead, other_user):
    api_client.force_authenticate(other_user)

    response = api_client.get(reverse("leads-detail", args=[lead.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_unrelated_agent_cannot_access_lead(api_client, lead, agent):
    api_client.force_authenticate(agent)

    response = api_client.get(reverse("leads-detail", args=[lead.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_assigned_agent_requires_active_property_capability(api_client, lead, agent):
    lead.assigned_to = agent
    lead.save(update_fields=["assigned_to", "updated_at"])
    assign_property(lead.property, agent)
    api_client.force_authenticate(agent)

    response = api_client.get(reverse("leads-detail", args=[lead.id]))

    assert response.status_code == 200
    assert response.data["id"] == str(lead.id)


@pytest.mark.django_db
def test_revoked_assignment_removes_lead_access(api_client, lead, agent):
    lead.assigned_to = agent
    lead.save(update_fields=["assigned_to", "updated_at"])
    assign_property(lead.property, agent, status=PropertyAssignmentStatus.REVOKED)
    api_client.force_authenticate(agent)

    response = api_client.get(reverse("leads-detail", args=[lead.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_admin_can_access_lead(api_client, lead, admin_user):
    api_client.force_authenticate(admin_user)

    response = api_client.get(reverse("leads-detail", args=[lead.id]))

    assert response.status_code == 200


@pytest.mark.django_db
def test_owner_can_assign_only_property_authorized_agent(api_client, lead, user, agent):
    api_client.force_authenticate(user)

    rejected = api_client.post(
        reverse("leads-assign", args=[lead.id]),
        {"assigned_to_id": str(agent.id)},
        format="json",
    )
    assert rejected.status_code == 400

    assign_property(lead.property, agent)
    response = api_client.post(
        reverse("leads-assign", args=[lead.id]),
        {"assigned_to_id": str(agent.id)},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["assigned_to"]["email"] == agent.email
    assert AuditLog.objects.filter(action="lead_assigned").exists()


@pytest.mark.django_db
def test_pipeline_transition_and_invalid_transition(api_client, lead, user):
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("leads-transition", args=[lead.id]),
        {"pipeline_stage": LeadPipelineStage.CONTACTED},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["pipeline_stage"] == LeadPipelineStage.CONTACTED

    rejected = api_client.post(
        reverse("leads-transition", args=[lead.id]),
        {"pipeline_stage": LeadPipelineStage.CONVERTED},
        format="json",
    )
    assert rejected.status_code == 400
    assert AuditLog.objects.filter(action="lead_pipeline_changed").exists()


@pytest.mark.django_db
def test_authorized_user_can_log_and_view_lead_activity(api_client, lead, user):
    api_client.force_authenticate(user)
    scheduled_for = timezone.now() + timezone.timedelta(days=1)

    created = api_client.post(
        reverse("leads-log-activity", args=[lead.id]),
        {
            "activity_type": LeadActivityType.FOLLOW_UP_SCHEDULED,
            "note": "Send updated brochure.",
            "scheduled_for": scheduled_for.isoformat(),
        },
        format="json",
    )
    assert created.status_code == 201

    listed = api_client.get(reverse("leads-list-activities", args=[lead.id]))

    assert listed.status_code == 200
    assert len(listed.data) == 1
    assert listed.data[0]["note"] == "Send updated brochure."
    assert AuditLog.objects.filter(action="lead_activity_logged").exists()


@pytest.mark.django_db
def test_lead_dashboard_metrics_are_scoped_to_authorized_user(
    api_client,
    lead,
    user,
    other_user,
    property_listing,
):
    Inquiry.objects.create(
        property=property_listing,
        interested_user=other_user,
        property_owner=user,
        inquiry_type=InquiryType.PURCHASE,
        pipeline_stage=LeadPipelineStage.CONTACTED,
    )
    api_client.force_authenticate(user)

    response = api_client.get(reverse("dashboard-leads-summary"))

    assert response.status_code == 200
    assert response.data["total_leads"] == 2
    assert response.data["new_leads"] == 1
    assert response.data["contacted_leads"] == 1
