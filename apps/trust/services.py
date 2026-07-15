"""Service-layer verification decision logic.

Mirrors apps.accounts.services.decide_role_request: self-review blocking,
transition validation, reviewer bookkeeping, and audit logging all in one
place, called from admin views rather than duplicated inline per action.
"""

from __future__ import annotations

from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import create_audit_log
from apps.trust.models import PropertyVerification, VerificationRequest


def decide_verification_request(
    *,
    actor: User,
    verification_request: VerificationRequest,
    status: str,
    rejection_reason: str = "",
    review_notes: str = "",
    expiry_date=None,
) -> VerificationRequest:
    if actor.id == verification_request.user_id:
        raise ValueError("Reviewers cannot review their own verification request.")

    if not verification_request.can_transition_to(status):
        raise ValueError(
            f"Verification cannot move from {verification_request.status} to {status}."
        )

    verification_request.status = status
    verification_request.reviewer = actor
    verification_request.reviewed_at = timezone.now()
    update_fields = ["status", "reviewer", "reviewed_at", "updated_at"]

    if rejection_reason:
        verification_request.rejection_reason = rejection_reason
        update_fields.append("rejection_reason")
    if review_notes:
        verification_request.review_notes = review_notes
        update_fields.append("review_notes")
    if expiry_date is not None:
        verification_request.expiry_date = expiry_date
        update_fields.append("expiry_date")

    verification_request.save(update_fields=update_fields)
    create_audit_log(
        actor=actor,
        action=f"verification.{status}",
        entity=verification_request,
        metadata={
            "verification_type": verification_request.verification_type,
            "user_id": str(verification_request.user_id),
        },
    )
    return verification_request


def decide_property_verification_request(
    *,
    actor: User,
    property_verification: PropertyVerification,
    status: str,
    rejection_reason: str = "",
    expiry_date=None,
) -> PropertyVerification:
    if actor.id == property_verification.submitted_by_id:
        raise ValueError("Reviewers cannot review their own property verification submission.")

    if not property_verification.can_transition_to(status):
        raise ValueError(
            f"Property verification cannot move from {property_verification.status} to {status}."
        )

    property_verification.status = status
    property_verification.reviewer = actor
    property_verification.reviewed_at = timezone.now()
    update_fields = ["status", "reviewer", "reviewed_at", "updated_at"]

    if rejection_reason:
        property_verification.rejection_reason = rejection_reason
        update_fields.append("rejection_reason")
    if expiry_date is not None:
        property_verification.expiry_date = expiry_date
        update_fields.append("expiry_date")

    # Snapshot property identity fields at approval time, used later by
    # the material-edit invalidation rule to detect drift after approval.
    if status == "approved":
        property_verification.verified_snapshot = {
            "address": property_verification.property.address,
            "price": str(property_verification.property.price),
            "listing_type": property_verification.property.listing_type,
        }
        update_fields.append("verified_snapshot")

    property_verification.save(update_fields=update_fields)
    create_audit_log(
        actor=actor,
        action=f"property_verification.{status}",
        entity=property_verification,
        metadata={"property_id": str(property_verification.property_id)},
    )
    return property_verification
