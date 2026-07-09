from __future__ import annotations

from apps.accounts.models import User
from apps.accounts.services import create_audit_log
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
