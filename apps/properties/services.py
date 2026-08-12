from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import create_audit_log, user_is_admin
from apps.notifications.choices import NotificationType
from apps.notifications.services import create_notification
from apps.properties.choices import (
    PropertyAssignmentCapability,
    PropertyAssignmentStatus,
    PropertyAssignmentType,
)
from apps.properties.models import Inquiry, Property, PropertyAssignment, RentalApplication, Viewing
from apps.trust.choices import VerificationStatus, VerificationType
from apps.trust.models import VerificationRequest


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
    notification_event = (metadata or {}).get("notification_event")
    if notification_event == "InquiryCreated":
        create_notification(
            recipient=inquiry.property_owner,
            notification_type=NotificationType.INQUIRY_CREATED,
            title="New inquiry received",
            body=f"You have a new inquiry on {inquiry.property.title}.",
            related_entity=inquiry,
        )
    elif notification_event == "InquiryStatusChanged":
        create_notification(
            recipient=inquiry.interested_user,
            notification_type=NotificationType.INQUIRY_STATUS_CHANGED,
            title="Inquiry status updated",
            body=f"Your inquiry status changed to {inquiry.status}.",
            related_entity=inquiry,
        )
    elif notification_event == "LeadStageChanged":
        create_notification(
            recipient=inquiry.assigned_to or inquiry.property_owner,
            notification_type=NotificationType.LEAD_STAGE_CHANGED,
            title="Lead stage updated",
            body=f"Lead stage changed to {inquiry.pipeline_stage}.",
            related_entity=inquiry,
        )


def emit_lead_assigned_event(
    *,
    actor: User,
    inquiry: Inquiry,
    metadata: dict | None = None,
) -> None:
    create_audit_log(
        actor=actor,
        action="lead_assigned",
        entity=inquiry,
        metadata={
            "assigned_to_id": str(inquiry.assigned_to_id) if inquiry.assigned_to_id else None,
            "property_id": str(inquiry.property_id),
            **(metadata or {}),
        },
    )
    if inquiry.assigned_to_id:
        create_notification(
            recipient=inquiry.assigned_to,
            notification_type=NotificationType.LEAD_ASSIGNED,
            title="Lead assigned to you",
            body=f"You were assigned a lead for {inquiry.property.title}.",
            related_entity=inquiry,
        )


def emit_lead_reassigned_event(
    *,
    actor: User,
    inquiry: Inquiry,
    previous_assigned_to_id: str | None,
    metadata: dict | None = None,
) -> None:
    create_audit_log(
        actor=actor,
        action="lead_reassigned",
        entity=inquiry,
        metadata={
            "previous_assigned_to_id": previous_assigned_to_id,
            "assigned_to_id": str(inquiry.assigned_to_id) if inquiry.assigned_to_id else None,
            "property_id": str(inquiry.property_id),
            **(metadata or {}),
        },
    )
    if inquiry.assigned_to_id:
        create_notification(
            recipient=inquiry.assigned_to,
            notification_type=NotificationType.LEAD_ASSIGNED,
            title="Lead reassigned to you",
            body=f"You were assigned a lead for {inquiry.property.title}.",
            related_entity=inquiry,
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
    notification_event = (metadata or {}).get("notification_event")
    viewing_event_map = {
        "ViewingRequested": (
            NotificationType.VIEWING_REQUESTED,
            viewing.property_owner,
            "New viewing request",
        ),
        "ViewingConfirmed": (
            NotificationType.VIEWING_CONFIRMED,
            viewing.requester,
            "Viewing confirmed",
        ),
        "ViewingRescheduled": (
            NotificationType.VIEWING_RESCHEDULED,
            viewing.requester,
            "Viewing rescheduled",
        ),
        "ViewingCancelled": (
            NotificationType.VIEWING_CANCELLED,
            viewing.requester,
            "Viewing cancelled",
        ),
    }
    if notification_event in viewing_event_map:
        notification_type, recipient, title = viewing_event_map[notification_event]
        create_notification(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            body=f"Viewing status: {viewing.status}.",
            related_entity=viewing,
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
    notification_event = (metadata or {}).get("notification_event")
    application_recipient_map = {
        "ApplicationSubmitted": application.property_owner,
        "ApplicationUnderReview": application.applicant,
        "ApplicationApproved": application.applicant,
        "ApplicationRejected": application.applicant,
        "ApplicationWithdrawn": application.property_owner,
    }
    if notification_event in application_recipient_map:
        create_notification(
            recipient=application_recipient_map[notification_event],
            notification_type=NotificationType.APPLICATION_STATUS_CHANGED,
            title=f"Application {notification_event.replace('Application', '')}",
            body=f"Application status: {application.status}.",
            related_entity=application,
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
    return any(
        capability_value in (assignment.capabilities or [])
        and _assignment_principal_is_eligible(assignment)
        for assignment in assignments
    )


def property_ids_for_user_capability(
    user: User,
    capability: str | PropertyAssignmentCapability,
) -> list:
    if not user or not user.is_authenticated or user.is_suspended or not user.is_active:
        return []
    capability_value = str(capability)
    assignments = PropertyAssignment.objects.filter(
        user=user,
        status=PropertyAssignmentStatus.ACTIVE,
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
    return [
        assignment.property_id
        for assignment in assignments
        if capability_value in (assignment.capabilities or [])
        and _assignment_principal_is_eligible(assignment)
    ]


def _assignment_principal_is_eligible(assignment: PropertyAssignment) -> bool:
    if assignment.relationship_type != PropertyAssignmentType.PROPERTY_MANAGER:
        return True
    today = timezone.localdate()
    return VerificationRequest.objects.filter(
        user=assignment.user,
        verification_type__in=[VerificationType.AGENT, VerificationType.LANDLORD],
        status=VerificationStatus.APPROVED,
    ).filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today)).exists()


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
