"""Service functions for payments state transitions and audit logging.

This module is proof-tracking/recordkeeping only. Nothing here represents
escrow, custody, or payment processing -- see the Transaction docstring
in models.py. Wording surfaced to users about any of these transitions
must stick to "uploaded" / "pending review" / "accepted" / "rejected" /
"disputed" -- never "payment completed" or similar guarantee language,
unless PM/legal have separately approved it.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.accounts.services import create_audit_log
from apps.payments.choices import DisputeStatus, MilestoneStatus, TransactionStatus
from apps.payments.models import (
    PaymentDispute,
    PaymentMilestone,
    PaymentProof,
    Transaction,
)
from apps.payments.validators import compute_checksum, sanitize_original_filename


def _transition(instance, new_status: str, actor, action: str, metadata: dict | None = None):
    """Validate and apply a status transition, then record an audit event.

    Shared by Transaction and PaymentMilestone, both of which expose the
    same can_transition_to(new_status) contract on their model classes.
    """
    if not instance.can_transition_to(new_status):
        raise ValidationError(
            f"Cannot transition {instance.__class__.__name__} from "
            f"'{instance.status}' to '{new_status}'."
        )
    old_status = instance.status
    instance.status = new_status
    instance.save(update_fields=["status", "updated_at"])
    create_audit_log(
        actor,
        action,
        instance,
        metadata={"from": old_status, "to": new_status, **(metadata or {})},
    )
    return instance


@db_transaction.atomic
def create_transaction(
    *, property, buyer, owner, actor, application=None, currency="NGN", notes=""
):
    if buyer.id == owner.id:
        raise ValidationError("Buyer and owner cannot be the same user.")
    if property.owner_id != owner.id:
        raise ValidationError("Transaction owner must match the property owner.")
    if application:
        if Transaction.objects.filter(application=application).exists():
            raise ValidationError("A transaction already exists for this application.")
        if application.property_id != property.id:
            raise ValidationError("Application must belong to the transaction property.")
        if application.applicant_id != buyer.id:
            raise ValidationError("Transaction buyer must match the application applicant.")
        if application.property_owner_id != owner.id:
            raise ValidationError("Transaction owner must match the application owner.")
    txn = Transaction.objects.create(
        property=property,
        buyer=buyer,
        owner=owner,
        application=application,
        currency=currency,
        notes=notes,
    )
    create_audit_log(
        actor, "transaction_created", txn, metadata={"property_id": str(property.id)}
    )
    return txn


def activate_transaction(transaction: Transaction, actor):
    return _transition(transaction, TransactionStatus.ACTIVE, actor, "transaction_activated")


def complete_transaction(transaction: Transaction, actor):
    return _transition(transaction, TransactionStatus.COMPLETED, actor, "transaction_completed")


def cancel_transaction(transaction: Transaction, actor, reason: str = ""):
    return _transition(
        transaction, TransactionStatus.CANCELLED, actor, "transaction_cancelled",
        metadata={"reason": reason},
    )


@db_transaction.atomic
def create_milestone(
    *, transaction: Transaction, actor, title, amount,
    description="", currency=None, due_date=None, order=0,
):
    if amount <= 0:
        raise ValidationError("Milestone amount must be greater than zero.")
    milestone = PaymentMilestone.objects.create(
        transaction=transaction,
        title=title,
        description=description,
        amount=amount,
        currency=currency or transaction.currency,
        due_date=due_date,
        order=order,
    )
    create_audit_log(actor, "milestone_created", milestone, metadata={"amount": str(amount)})
    return milestone


@db_transaction.atomic
def submit_payment_proof(
    *, milestone: PaymentMilestone, uploaded_by, file,
    amount_claimed, reference="", note="",
):
    """Attach proof evidence to a milestone and move it to proof_uploaded.

    Valid from PENDING (first submission) or REJECTED (resubmission after
    a reviewer rejected an earlier proof).
    """
    if milestone.status not in {MilestoneStatus.PENDING, MilestoneStatus.REJECTED}:
        raise ValidationError(
            f"Cannot submit a payment proof while milestone is '{milestone.status}'."
        )
    if uploaded_by.id != milestone.transaction.buyer_id:
        raise ValidationError("Only the buyer can submit payment proof.")
    if amount_claimed <= 0:
        raise ValidationError("Claimed amount must be greater than zero.")
    checksum = compute_checksum(file)
    proof = PaymentProof.objects.create(
        milestone=milestone,
        uploaded_by=uploaded_by,
        file=file,
        original_filename=sanitize_original_filename(file.name),
        file_size=file.size,
        checksum=checksum,
        amount_claimed=amount_claimed,
        reference=reference,
        note=note,
    )
    old_status = milestone.status
    milestone.status = MilestoneStatus.PROOF_UPLOADED
    milestone.save(update_fields=["status", "updated_at"])
    create_audit_log(
        uploaded_by,
        "payment_proof_uploaded",
        proof,
        metadata={"milestone_id": str(milestone.id), "from": old_status, "to": milestone.status},
    )
    return proof


def start_milestone_review(milestone: PaymentMilestone, actor):
    """A reviewer claims a proof-uploaded milestone for review."""
    return _transition(
        milestone, MilestoneStatus.UNDER_REVIEW, actor, "payment_proof_reviewed",
        metadata={"stage": "review_started"},
    )


def accept_milestone(milestone: PaymentMilestone, actor, note: str = ""):
    return _transition(
        milestone, MilestoneStatus.ACCEPTED, actor, "milestone_accepted", metadata={"note": note}
    )


def reject_milestone(milestone: PaymentMilestone, actor, note: str = ""):
    return _transition(
        milestone, MilestoneStatus.REJECTED, actor, "milestone_rejected", metadata={"note": note}
    )


def cancel_milestone(milestone: PaymentMilestone, actor, reason: str = ""):
    return _transition(
        milestone, MilestoneStatus.CANCELLED, actor, "milestone_cancelled",
        metadata={"reason": reason},
    )


@db_transaction.atomic
def open_dispute(
    *, transaction: Transaction, opened_by, reason: str,
    milestone: PaymentMilestone | None = None,
):
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("Dispute reason is required.")
    if opened_by.id not in {transaction.buyer_id, transaction.owner_id}:
        raise ValidationError("Only transaction participants can open disputes.")
    if milestone and milestone.transaction_id != transaction.id:
        raise ValidationError("Milestone must belong to the transaction.")
    dispute = PaymentDispute.objects.create(
        transaction=transaction,
        milestone=milestone,
        opened_by=opened_by,
        reason=reason,
    )
    milestone_id = str(milestone.id) if milestone else None
    create_audit_log(
        opened_by,
        "dispute_opened",
        dispute,
        metadata={"transaction_id": str(transaction.id), "milestone_id": milestone_id},
    )
    if milestone is not None and milestone.can_transition_to(MilestoneStatus.DISPUTED):
        milestone.status = MilestoneStatus.DISPUTED
        milestone.save(update_fields=["status", "updated_at"])
    if transaction.can_transition_to(TransactionStatus.DISPUTED):
        transaction.status = TransactionStatus.DISPUTED
        transaction.save(update_fields=["status", "updated_at"])
    return dispute


@db_transaction.atomic
def resolve_dispute(
    dispute: PaymentDispute, actor, resolution_note: str,
    status: str = DisputeStatus.RESOLVED,
):
    if status not in {DisputeStatus.RESOLVED, DisputeStatus.CLOSED}:
        raise ValidationError("Dispute can only be resolved to 'resolved' or 'closed'.")
    dispute.status = status
    dispute.resolution_note = resolution_note
    dispute.resolved_by = actor
    dispute.resolved_at = timezone.now()
    dispute.save(
        update_fields=["status", "resolution_note", "resolved_by", "resolved_at", "updated_at"]
    )
    create_audit_log(actor, "dispute_resolved", dispute, metadata={"status": status})
    return dispute
