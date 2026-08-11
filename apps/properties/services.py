from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import create_audit_log, user_is_admin
from apps.properties.choices import PropertyAssignmentCapability, PropertyAssignmentStatus
from apps.properties.models import Inquiry, Property, PropertyAssignment, RentalApplication, Viewing


def emit_inquiry_event(
    *,
    actor: User,
    inquiry: Inquiry,
    event_name: str,
    metadata: dict | None = None,
) -> None:
    create_audit_log(
        actor=actor,
        action=event_name,
        entity=inquiry,
        metadata={
            "property_id": str(inquiry.property_id),
            "interested_user_id": str(inquiry.interested_user_id),
            "property_owner_id": str(inquiry.property_owner_id),
            "status": inquiry.status,
            **(metadata or {}),
        },
    )


def emit_viewing_event(
    *,
    actor: User,
    viewing: Viewing,
    event_name: str,
    metadata: dict | None = None,
) -> None:
    create_audit_log(
        actor=actor,
        action=event_name,
        entity=viewing,
        metadata={
            "inquiry_id": str(viewing.inquiry_id),
            "property_id": str(viewing.property_id),
            "requester_id": str(viewing.requester_id),
            "property_owner_id": str(viewing.property_owner_id),
            "status": viewing.status,
            **(metadata or {}),
        },
    )


def emit_application_event(
    *,
    actor: User,
    application: RentalApplication,
    event_name: str,
    metadata: dict | None = None,
) -> None:
    create_audit_log(
        actor=actor,
        action=event_name,
        entity=application,
        metadata={
            "property_id": str(application.property_id),
            "applicant_id": str(application.applicant_id),
            "property_owner_id": str(application.property_owner_id),
            "inquiry_id": str(application.inquiry_id) if application.inquiry_id else "",
            "viewing_id": str(application.viewing_id) if application.viewing_id else "",
            "status": application.status,
            **(metadata or {}),
        },
    )


def user_has_property_capability(
    user: User,
    prop: Property,
    capability: str | PropertyAssignmentCapability,
) -> bool:
    if not user or not user.is_authenticated or user.is_suspended or not user.is_active:
        return False
    if user_is_admin(user) or prop.owner_id == user.id:
        return True
    assignments = PropertyAssignment.objects.filter(
        property=prop,
        user=user,
        status=PropertyAssignmentStatus.ACTIVE,
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
    capability_value = str(capability)
    return any(capability_value in (assignment.capabilities or []) for assignment in assignments)


def emit_property_assignment_event(
    *,
    actor: User,
    assignment: PropertyAssignment,
    event_name: str,
    metadata: dict | None = None,
) -> None:
    create_audit_log(
        actor=actor,
        action=event_name,
        entity=assignment,
        metadata={
            "property_id": str(assignment.property_id),
            "user_id": str(assignment.user_id),
            "relationship_type": assignment.relationship_type,
            "status": assignment.status,
            "capabilities": assignment.capabilities,
            **(metadata or {}),
        },
    )
