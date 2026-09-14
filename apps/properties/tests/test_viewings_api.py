from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import AuditLog
from apps.properties.choices import (
    InquiryStatus,
    InquiryType,
    PropertyAssignmentCapability,
    PropertyAssignmentStatus,
    PropertyAssignmentType,
    PropertyStatus,
    ViewingStatus,
    ViewingType,
)
from apps.properties.models import Inquiry, Property, PropertyAssignment, Viewing


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
    )


def future_iso(days=5):
    return (timezone.now() + timedelta(days=days)).isoformat()


def assign_viewing_manager(prop, agent, **overrides):
    payload = {
        "property": prop,
        "user": agent,
        "relationship_type": PropertyAssignmentType.AGENT,
        "status": PropertyAssignmentStatus.ACTIVE,
        "capabilities": [PropertyAssignmentCapability.MANAGE_VIEWINGS],
        "assigned_by": prop.owner,
    }
    payload.update(overrides)
    return PropertyAssignment.objects.create(**payload)


def make_viewing_for_property(prop, requester, *, status=ViewingStatus.REQUESTED):
    inquiry = Inquiry.objects.create(
        property=prop,
        interested_user=requester,
        property_owner=prop.owner,
        inquiry_type=InquiryType.PURCHASE,
    )
    return Viewing.objects.create(
        inquiry=inquiry,
        property=prop,
        requester=requester,
        property_owner=prop.owner,
        viewing_type=ViewingType.PHYSICAL,
        preferred_date=timezone.localdate() + timedelta(days=3),
        preferred_time="14:00:00",
        status=status,
    )


def make_property(owner, title="Delegated Viewing Property"):
    return Property.objects.create(
        owner=owner,
        title=title,
        description=f"{title} description.",
        property_type="apartment",
        listing_type="rent",
        price="2500000.00",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        address="Viewing Street",
        status=PropertyStatus.APPROVED,
    )


@pytest.mark.django_db
def test_authenticated_user_can_create_viewing_request(api_client, inquiry, other_user):
    api_client.force_authenticate(other_user)

    response = api_client.post(
        reverse("viewings-list"),
        {
            "inquiry_id": str(inquiry.id),
            "viewing_type": ViewingType.VIRTUAL,
            "preferred_date": str(timezone.localdate() + timedelta(days=2)),
            "preferred_time": "10:30:00",
            "notes": "A virtual tour works best.",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["status"] == ViewingStatus.REQUESTED
    assert response.data["property"]["id"] == str(inquiry.property_id)
    assert response.data["requester"]["email"] == other_user.email
    assert Viewing.objects.filter(inquiry=inquiry, requester=other_user).exists()
    assert AuditLog.objects.filter(action="viewing.created").exists()


@pytest.mark.django_db
def test_user_cannot_create_viewing_for_someone_elses_inquiry(api_client, inquiry, user):
    api_client.force_authenticate(user)

    response = api_client.post(
        reverse("viewings-list"),
        {
            "inquiry_id": str(inquiry.id),
            "viewing_type": ViewingType.PHYSICAL,
            "preferred_date": str(timezone.localdate() + timedelta(days=2)),
            "preferred_time": "10:30:00",
        },
        format="json",
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_requester_lists_their_viewings(api_client, viewing, other_user):
    api_client.force_authenticate(other_user)

    response = api_client.get(reverse("viewings-list"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(viewing.id)


@pytest.mark.django_db
def test_owner_lists_received_viewings(api_client, viewing, user):
    api_client.force_authenticate(user)

    response = api_client.get(reverse("viewings-received"))

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == str(viewing.id)
    assert response.data["results"][0]["can_manage_viewing"] is True


@pytest.mark.django_db
def test_assigned_agent_with_manage_viewings_can_list_and_retrieve_received_viewing(
    api_client,
    viewing,
    user,
    django_user_model,
):
    agent = django_user_model.objects.create_user(
        email="viewing-agent@example.com",
        password="Str0ngPass123!",
    )
    assign_viewing_manager(viewing.property, agent)
    api_client.force_authenticate(agent)

    list_response = api_client.get(reverse("viewings-received"))
    detail_response = api_client.get(reverse("viewings-detail", kwargs={"pk": viewing.id}))

    assert list_response.status_code == 200
    assert {item["id"] for item in list_response.data["results"]} == {str(viewing.id)}
    assert detail_response.status_code == 200
    assert detail_response.data["can_manage_viewing"] is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("assignment_status", "expires_in_days", "capabilities"),
    [
        (PropertyAssignmentStatus.ACTIVE, None, [PropertyAssignmentCapability.MANAGE_LEADS]),
        (PropertyAssignmentStatus.REVOKED, None, [PropertyAssignmentCapability.MANAGE_VIEWINGS]),
        (PropertyAssignmentStatus.SUSPENDED, None, [PropertyAssignmentCapability.MANAGE_VIEWINGS]),
        (PropertyAssignmentStatus.ACTIVE, -1, [PropertyAssignmentCapability.MANAGE_VIEWINGS]),
    ],
)
def test_agent_without_current_manage_viewings_assignment_cannot_access_received_viewing(
    api_client,
    viewing,
    django_user_model,
    assignment_status,
    expires_in_days,
    capabilities,
):
    agent = django_user_model.objects.create_user(
        email=f"blocked-viewing-agent-{assignment_status}-{expires_in_days}@example.com",
        password="Str0ngPass123!",
    )
    expires_at = None
    if expires_in_days is not None:
        expires_at = timezone.now() + timedelta(days=expires_in_days)
    assign_viewing_manager(
        viewing.property,
        agent,
        status=assignment_status,
        expires_at=expires_at,
        capabilities=capabilities,
    )
    api_client.force_authenticate(agent)

    list_response = api_client.get(reverse("viewings-received"))
    detail_response = api_client.get(reverse("viewings-detail", kwargs={"pk": viewing.id}))
    confirm_response = api_client.post(
        reverse("viewings-confirm", kwargs={"pk": viewing.id}),
        {"confirmed_datetime": future_iso()},
        format="json",
    )

    assert list_response.status_code == 200
    assert list_response.data["count"] == 0
    assert detail_response.status_code == 404
    assert confirm_response.status_code == 404


@pytest.mark.django_db
def test_assigned_agent_with_manage_viewings_cannot_cross_property_boundary(
    api_client,
    viewing,
    other_user,
    django_user_model,
):
    agent = django_user_model.objects.create_user(
        email="cross-boundary-agent@example.com",
        password="Str0ngPass123!",
    )
    other_owner = django_user_model.objects.create_user(
        email="other-viewing-owner@example.com",
        password="Str0ngPass123!",
    )
    other_property = make_property(other_owner, "Other Viewing Property")
    other_viewing = make_viewing_for_property(other_property, other_user)
    assign_viewing_manager(viewing.property, agent)
    api_client.force_authenticate(agent)

    response = api_client.get(reverse("viewings-detail", kwargs={"pk": other_viewing.id}))
    action = api_client.post(
        reverse("viewings-confirm", kwargs={"pk": other_viewing.id}),
        {"confirmed_datetime": future_iso()},
        format="json",
    )

    assert response.status_code == 404
    assert action.status_code == 404


@pytest.mark.django_db
def test_assigned_agent_with_manage_viewings_can_manage_lifecycle_and_notes(
    api_client,
    viewing,
    django_user_model,
):
    agent = django_user_model.objects.create_user(
        email="viewing-manager@example.com",
        password="Str0ngPass123!",
    )
    assign_viewing_manager(viewing.property, agent)
    api_client.force_authenticate(agent)

    confirmed = api_client.post(
        reverse("viewings-confirm", kwargs={"pk": viewing.id}),
        {
            "confirmed_datetime": future_iso(),
            "meeting_location": "Estate reception",
            "notes": "Shared access note.",
        },
        format="json",
    )
    assert confirmed.status_code == 200
    assert confirmed.data["status"] == ViewingStatus.CONFIRMED
    assert confirmed.data["can_manage_viewing"] is True

    notes = api_client.patch(
        reverse("viewings-update-notes", kwargs={"pk": viewing.id}),
        {"notes": "Updated shared participant note."},
        format="json",
    )
    assert notes.status_code == 200
    assert notes.data["notes"] == "Updated shared participant note."

    completed = api_client.post(reverse("viewings-complete", kwargs={"pk": viewing.id}))
    assert completed.status_code == 200
    assert completed.data["status"] == ViewingStatus.COMPLETED


@pytest.mark.django_db
def test_assigned_agent_with_manage_viewings_can_reschedule_and_cancel(
    api_client,
    viewing,
    django_user_model,
):
    agent = django_user_model.objects.create_user(
        email="viewing-rescheduler@example.com",
        password="Str0ngPass123!",
    )
    assign_viewing_manager(viewing.property, agent)
    api_client.force_authenticate(agent)

    rescheduled = api_client.post(
        reverse("viewings-reschedule", kwargs={"pk": viewing.id}),
        {"confirmed_datetime": future_iso(6), "meeting_location": "Virtual link pending"},
        format="json",
    )
    cancelled = api_client.post(
        reverse("viewings-cancel", kwargs={"pk": viewing.id}),
        {"notes": "Requester asked for a later slot."},
        format="json",
    )

    assert rescheduled.status_code == 200
    assert rescheduled.data["status"] == ViewingStatus.RESCHEDULED
    assert cancelled.status_code == 200
    assert cancelled.data["status"] == ViewingStatus.CANCELLED


@pytest.mark.django_db
def test_only_owner_can_confirm_viewing(api_client, viewing, other_user, user):
    api_client.force_authenticate(other_user)
    forbidden = api_client.post(
        reverse("viewings-confirm", kwargs={"pk": viewing.id}),
        {"confirmed_datetime": future_iso()},
        format="json",
    )
    assert forbidden.status_code == 403

    api_client.force_authenticate(user)
    response = api_client.post(
        reverse("viewings-confirm", kwargs={"pk": viewing.id}),
        {
            "confirmed_datetime": future_iso(),
            "meeting_location": "Lobby reception",
            "meeting_link": "",
            "notes": "Bring an ID.",
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["status"] == ViewingStatus.CONFIRMED
    assert response.data["meeting_location"] == "Lobby reception"
    viewing.inquiry.refresh_from_db()
    assert viewing.inquiry.status == InquiryStatus.VIEWING_SCHEDULED
    assert AuditLog.objects.filter(action="viewing.confirmed").exists()


@pytest.mark.django_db
def test_owner_can_reschedule_then_confirm(api_client, viewing, user):
    api_client.force_authenticate(user)

    rescheduled = api_client.post(
        reverse("viewings-reschedule", kwargs={"pk": viewing.id}),
        {"confirmed_datetime": future_iso(6), "meeting_location": "Zoom"},
        format="json",
    )
    assert rescheduled.status_code == 200
    assert rescheduled.data["status"] == ViewingStatus.RESCHEDULED

    confirmed = api_client.post(
        reverse("viewings-confirm", kwargs={"pk": viewing.id}),
        {"confirmed_datetime": future_iso(7), "meeting_location": "Zoom"},
        format="json",
    )
    assert confirmed.status_code == 200
    assert confirmed.data["status"] == ViewingStatus.CONFIRMED


@pytest.mark.django_db
def test_invalid_transition_is_rejected(api_client, viewing, user):
    api_client.force_authenticate(user)

    response = api_client.post(reverse("viewings-complete", kwargs={"pk": viewing.id}))

    assert response.status_code == 400
    viewing.refresh_from_db()
    assert viewing.status == ViewingStatus.REQUESTED


@pytest.mark.django_db
def test_participant_can_cancel_viewing(api_client, viewing, other_user):
    api_client.force_authenticate(other_user)

    response = api_client.post(
        reverse("viewings-cancel", kwargs={"pk": viewing.id}),
        {"notes": "Travel plans changed."},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["status"] == ViewingStatus.CANCELLED
    assert response.data["notes"] == "Travel plans changed."
    assert AuditLog.objects.filter(action="viewing.cancelled").exists()


@pytest.mark.django_db
def test_owner_can_complete_confirmed_viewing(api_client, viewing, user):
    viewing.status = ViewingStatus.CONFIRMED
    viewing.confirmed_datetime = timezone.now() + timedelta(days=2)
    viewing.save(update_fields=["status", "confirmed_datetime", "updated_at"])
    api_client.force_authenticate(user)

    response = api_client.post(reverse("viewings-complete", kwargs={"pk": viewing.id}))

    assert response.status_code == 200
    assert response.data["status"] == ViewingStatus.COMPLETED
    assert AuditLog.objects.filter(action="viewing.completed").exists()


@pytest.mark.django_db
def test_participant_can_update_viewing_notes(api_client, viewing, other_user):
    api_client.force_authenticate(other_user)

    response = api_client.patch(
        reverse("viewings-update-notes", kwargs={"pk": viewing.id}),
        {"notes": "Please send access instructions."},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["notes"] == "Please send access instructions."
