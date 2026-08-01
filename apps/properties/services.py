from __future__ import annotations

from apps.accounts.models import User
from apps.accounts.services import create_audit_log
from apps.notifications.choices import NotificationType
from apps.notifications.services import create_notification
from apps.properties.models import Inquiry, RentalApplication, Viewing


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
