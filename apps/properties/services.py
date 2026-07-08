from __future__ import annotations

from apps.accounts.models import User
from apps.accounts.services import create_audit_log
from apps.properties.models import Inquiry


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
