"""Service functions for payments state transitions and audit logging.

This module is proof-tracking/recordkeeping only. Nothing here represents
escrow, custody, or payment processing -- see the Transaction docstring
in models.py. Wording surfaced to users about any of these transitions
must stick to "uploaded" / "pending review" / "accepted" / "rejected" /
"disputed" -- never "payment completed" or similar guarantee language,
unless PM/legal have separately approved it.
"""

from __future__ import annotations

import hashlib
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.accounts.services import create_audit_log, user_is_admin
from apps.inspections.choices import InspectionRequestStatus
from apps.notifications.choices import NotificationType
from apps.notifications.services import create_notification
from apps.payments.choices import (
    DisputeStatus,
    EscrowConditionStatus,
    EscrowConditionType,
    EscrowFeeStatus,
    EscrowFeeType,
    EscrowFundingEventType,
    EscrowFundingStatus,
    EscrowIntegrationMode,
    EscrowProviderStatus,
    EscrowReconciliationRecordStatus,
    EscrowReconciliationStatus,
    EscrowRefundStatus,
    EscrowReleaseStatus,
    EscrowStatus,
    MilestoneStatus,
    ProviderWebhookProcessingStatus,
    ProviderWebhookSignatureStatus,
    TransactionStatus,
)
from apps.payments.escrow_adapters import get_escrow_provider_adapter
from apps.payments.models import (
    EscrowCondition,
    EscrowFundingEvent,
    EscrowProvider,
    EscrowReconciliationRecord,
    EscrowRefund,
    EscrowRelease,
    EscrowSettlement,
    EscrowSettlementAllocation,
    EscrowTransaction,
    PaymentDispute,
    PaymentMilestone,
    PaymentProof,
    ProviderWebhookEvent,
    Transaction,
)
from apps.payments.validators import compute_checksum, sanitize_original_filename
from apps.properties.choices import PropertyAssignmentCapability
from apps.properties.services import user_has_property_capability


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


def can_manage_escrow(user, transaction: Transaction) -> bool:
    if user_is_admin(user) or transaction.owner_id == user.id:
        return True
    return user_has_property_capability(
        user,
        transaction.property,
        PropertyAssignmentCapability.MANAGE_TRANSACTIONS,
    )


def can_view_escrow(user, escrow: EscrowTransaction) -> bool:
    transaction = escrow.transaction
    return (
        transaction.buyer_id == user.id
        or transaction.owner_id == user.id
        or can_manage_escrow(user, transaction)
    )


def _money(value) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_platform_fee(
    *, amount: Decimal, fee_type: str, fee_value: Decimal, provider_fee: Decimal = Decimal("0")
) -> Decimal:
    amount = _money(amount)
    fee_value = Decimal(fee_value or 0)
    if fee_type == EscrowFeeType.NONE:
        return Decimal("0.00")
    if fee_type == EscrowFeeType.FIXED:
        return _money(fee_value)
    if fee_type == EscrowFeeType.PERCENTAGE:
        return _money(amount * fee_value / Decimal("100"))
    if fee_type == EscrowFeeType.HYBRID:
        return _money((amount * fee_value / Decimal("100")) + Decimal(provider_fee or 0))
    raise ValidationError("Unsupported platform fee type.")


@db_transaction.atomic
def create_escrow_transaction(
    *,
    transaction: Transaction,
    provider: EscrowProvider,
    actor,
    expected_amount,
    currency: str | None = None,
    external_reference: str = "",
    platform_fee_type: str = EscrowFeeType.NONE,
    platform_fee_value=Decimal("0"),
    provider_fee=Decimal("0"),
    idempotency_key: str = "",
) -> EscrowTransaction:
    locked_transaction = Transaction.objects.select_for_update().get(id=transaction.id)
    escrow_candidate = EscrowTransaction(transaction=locked_transaction, provider=provider)
    if not can_view_escrow(actor, escrow_candidate):
        raise ValidationError("You are not allowed to create escrow for this transaction.")
    if EscrowTransaction.objects.filter(transaction=locked_transaction).exists():
        return EscrowTransaction.objects.select_related("transaction", "provider").get(
            transaction=locked_transaction
        )
    if provider.status not in {EscrowProviderStatus.ACTIVE, EscrowProviderStatus.SANDBOX}:
        raise ValidationError("Escrow provider is not active.")
    currency = (currency or locked_transaction.currency).upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValidationError("Currency must be a 3-letter ISO code.")
    if not provider.supports_currency(currency):
        raise ValidationError("Escrow provider does not support this currency.")
    expected_amount = _money(expected_amount)
    if expected_amount <= 0:
        raise ValidationError("Expected escrow amount must be greater than zero.")
    provider_fee = _money(provider_fee)
    expected_platform_fee = calculate_platform_fee(
        amount=expected_amount,
        fee_type=platform_fee_type,
        fee_value=platform_fee_value,
        provider_fee=provider_fee if platform_fee_type == EscrowFeeType.HYBRID else Decimal("0"),
    )
    escrow = EscrowTransaction.objects.create(
        transaction=locked_transaction,
        provider=provider,
        external_reference=external_reference,
        currency=currency,
        expected_amount=expected_amount,
        platform_fee_type=platform_fee_type,
        platform_fee_value=platform_fee_value or Decimal("0"),
        expected_platform_fee=expected_platform_fee,
        provider_fee=provider_fee,
        fee_status=(
            EscrowFeeStatus.NOT_APPLICABLE
            if platform_fee_type == EscrowFeeType.NONE
            else EscrowFeeStatus.CALCULATED
        ),
        created_by=actor,
        metadata={"idempotency_key": idempotency_key} if idempotency_key else {},
    )
    if provider.integration_mode in {EscrowIntegrationMode.MANUAL, EscrowIntegrationMode.SANDBOX}:
        adapter_reference = get_escrow_provider_adapter(provider).create_escrow(escrow=escrow)
        escrow.external_reference = external_reference or adapter_reference
        escrow.status = EscrowStatus.AWAITING_FUNDING
        escrow.save(update_fields=["external_reference", "status", "updated_at"])
    else:
        escrow.status = EscrowStatus.AWAITING_PROVIDER
        escrow.save(update_fields=["status", "updated_at"])
    create_audit_log(
        actor,
        "escrow_created",
        escrow,
        metadata={
            "transaction_id": str(locked_transaction.id),
            "provider": provider.slug,
            "expected_amount": str(expected_amount),
        },
    )
    _notify_participants(
        escrow,
        title="Escrow started",
        body="Escrow tracking has started for this transaction.",
        actor=actor,
    )
    return escrow


@db_transaction.atomic
def record_provider_reference(
    *, escrow: EscrowTransaction, actor, external_reference: str, note: str = ""
) -> EscrowTransaction:
    escrow = EscrowTransaction.objects.select_for_update().get(id=escrow.id)
    if not can_manage_escrow(actor, escrow.transaction):
        raise ValidationError("You are not allowed to manage this escrow.")
    external_reference = (external_reference or "").strip()
    if not external_reference:
        raise ValidationError("Provider reference is required.")
    escrow.external_reference = external_reference
    if escrow.status == EscrowStatus.AWAITING_PROVIDER:
        escrow.status = EscrowStatus.AWAITING_FUNDING
    escrow.save(update_fields=["external_reference", "status", "updated_at"])
    create_audit_log(
        actor,
        "escrow_provider_reference_recorded",
        escrow,
        metadata={"note": note, "reference": external_reference},
    )
    return escrow


@db_transaction.atomic
def record_funding_event(
    *,
    escrow: EscrowTransaction,
    amount,
    currency: str,
    provider_event_id: str,
    event_type: str = EscrowFundingEventType.FUNDING_CONFIRMED,
    actor=None,
    provider_reference: str = "",
    provider_status: str = "",
    occurred_at=None,
    raw_reference: str = "",
    metadata: dict | None = None,
) -> tuple[EscrowFundingEvent, bool]:
    escrow = EscrowTransaction.objects.select_for_update().get(id=escrow.id)
    provider_event_id = (provider_event_id or "").strip()
    if not provider_event_id:
        raise ValidationError("Provider event id is required.")
    existing = EscrowFundingEvent.objects.filter(
        escrow=escrow,
        provider_event_id=provider_event_id,
    ).first()
    if existing:
        return existing, False
    amount = _money(amount)
    currency = currency.upper()
    if currency != escrow.currency:
        raise ValidationError("Funding currency does not match escrow currency.")
    funding_event = EscrowFundingEvent.objects.create(
        escrow=escrow,
        provider_event_id=provider_event_id,
        provider_reference=provider_reference,
        amount=amount,
        currency=currency,
        event_type=event_type,
        provider_status=provider_status,
        occurred_at=occurred_at or timezone.now(),
        recorded_by=actor,
        raw_reference=raw_reference,
        metadata=metadata or {},
    )
    if event_type == EscrowFundingEventType.FUNDING_REVERSED:
        escrow.confirmed_funded_amount = max(
            Decimal("0.00"),
            _money(escrow.confirmed_funded_amount - amount),
        )
        escrow.funding_status = EscrowFundingStatus.REVERSED
    else:
        escrow.confirmed_funded_amount = _money(escrow.confirmed_funded_amount + amount)
        if escrow.confirmed_funded_amount < escrow.expected_amount:
            escrow.status = EscrowStatus.PARTIALLY_FUNDED
            escrow.funding_status = EscrowFundingStatus.PARTIALLY_CONFIRMED
        else:
            escrow.status = EscrowStatus.FUNDED
            escrow.funding_status = EscrowFundingStatus.CONFIRMED_BY_PROVIDER
            escrow.funded_at = timezone.now()
    escrow.save(
        update_fields=[
            "confirmed_funded_amount",
            "funding_status",
            "status",
            "funded_at",
            "updated_at",
        ]
    )
    create_audit_log(
        actor,
        "escrow_funding_confirmed",
        funding_event,
        metadata={
            "escrow_id": str(escrow.id),
            "amount": str(amount),
            "provider_event_id": provider_event_id,
        },
    )
    _notify_participants(
        escrow,
        title="Escrow funding updated",
        body="Funding has been recorded from the escrow provider.",
        actor=actor,
    )
    return funding_event, True


@db_transaction.atomic
def create_escrow_condition(
    *,
    escrow: EscrowTransaction,
    actor,
    condition_type: str,
    description: str = "",
    required: bool = True,
    inspection_request=None,
    construction_milestone=None,
) -> EscrowCondition:
    escrow = EscrowTransaction.objects.select_for_update().get(id=escrow.id)
    if not can_manage_escrow(actor, escrow.transaction):
        raise ValidationError("You are not allowed to manage this escrow.")
    condition = EscrowCondition.objects.create(
        escrow=escrow,
        condition_type=condition_type,
        description=description,
        required=required,
        inspection_request=inspection_request,
        construction_milestone=construction_milestone,
    )
    if escrow.status == EscrowStatus.FUNDED:
        escrow.status = EscrowStatus.CONDITIONS_PENDING
        escrow.save(update_fields=["status", "updated_at"])
    create_audit_log(actor, "escrow_condition_created", condition, metadata={})
    return condition


@db_transaction.atomic
def satisfy_escrow_condition(
    *, condition: EscrowCondition, actor, note: str = ""
) -> EscrowCondition:
    condition = EscrowCondition.objects.select_for_update().select_related("escrow").get(
        id=condition.id
    )
    if not can_manage_escrow(actor, condition.escrow.transaction):
        raise ValidationError("You are not allowed to manage this escrow condition.")
    _validate_condition_authority(condition)
    condition.status = EscrowConditionStatus.SATISFIED
    condition.satisfied_by = actor
    condition.satisfied_at = timezone.now()
    condition.failure_reason = ""
    condition.save(
        update_fields=[
            "status",
            "satisfied_by",
            "satisfied_at",
            "failure_reason",
            "updated_at",
        ]
    )
    create_audit_log(actor, "escrow_condition_satisfied", condition, metadata={"note": note})
    return condition


def _validate_condition_authority(condition: EscrowCondition) -> None:
    if condition.condition_type == EscrowConditionType.INSPECTION_PASSED:
        if not condition.inspection_request_id:
            raise ValidationError("Inspection condition requires a linked inspection request.")
        if condition.inspection_request.status != InspectionRequestStatus.COMPLETED:
            raise ValidationError("Linked inspection request is not completed.")
    if condition.condition_type == EscrowConditionType.CONSTRUCTION_MILESTONE_APPROVED:
        if not condition.construction_milestone_id:
            raise ValidationError("Construction condition requires a linked milestone.")
        if condition.construction_milestone.status != "completed":
            raise ValidationError("Linked construction milestone is not completed.")


def _required_conditions_satisfied(escrow: EscrowTransaction) -> bool:
    return not escrow.conditions.filter(
        required=True,
        status=EscrowConditionStatus.PENDING,
    ).exists()


def _has_open_dispute(escrow: EscrowTransaction) -> bool:
    return escrow.transaction.disputes.filter(
        status__in=[DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]
    ).exists()


@db_transaction.atomic
def request_release(
    *, escrow: EscrowTransaction, actor, amount=None, reason: str = "", idempotency_key: str = ""
) -> EscrowRelease:
    escrow = EscrowTransaction.objects.select_for_update().get(id=escrow.id)
    actor_is_buyer = actor.id == escrow.transaction.buyer_id
    if not (actor_is_buyer or can_manage_escrow(actor, escrow.transaction)):
        raise ValidationError("You are not allowed to request release for this escrow.")
    if _has_open_dispute(escrow):
        raise ValidationError("Escrow release is blocked while a dispute is open.")
    if escrow.status not in {
        EscrowStatus.FUNDED,
        EscrowStatus.CONDITIONS_PENDING,
        EscrowStatus.DISPUTED,
    }:
        raise ValidationError("Escrow is not eligible for release request.")
    if not _required_conditions_satisfied(escrow):
        raise ValidationError("Required release conditions are not satisfied.")
    amount = _money(amount or escrow.confirmed_funded_amount)
    if amount <= 0 or amount > escrow.confirmed_funded_amount:
        raise ValidationError("Release amount must be funded and greater than zero.")
    if idempotency_key:
        existing = EscrowRelease.objects.filter(
            escrow=escrow,
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return existing
    release = EscrowRelease.objects.create(
        escrow=escrow,
        amount=amount,
        currency=escrow.currency,
        requested_by=actor,
        reason=reason,
        idempotency_key=idempotency_key,
    )
    escrow.status = EscrowStatus.RELEASE_PENDING
    escrow.release_status = EscrowReleaseStatus.REQUESTED
    escrow.save(update_fields=["status", "release_status", "updated_at"])
    create_audit_log(
        actor,
        "escrow_release_requested",
        release,
        metadata={"escrow_id": str(escrow.id), "amount": str(amount)},
    )
    return release


@db_transaction.atomic
def approve_release(
    *, release: EscrowRelease, actor, provider_instruction_id: str = "", note: str = ""
) -> EscrowRelease:
    release = EscrowRelease.objects.select_for_update().select_related("escrow").get(id=release.id)
    escrow = EscrowTransaction.objects.select_for_update().get(id=release.escrow_id)
    if not can_manage_escrow(actor, escrow.transaction):
        raise ValidationError("You are not allowed to approve this release.")
    if release.status != EscrowReleaseStatus.REQUESTED:
        raise ValidationError("Only requested releases can be approved.")
    adapter_reference = get_escrow_provider_adapter(escrow.provider).request_release(
        release=release
    )
    release.status = EscrowReleaseStatus.SENT_TO_PROVIDER
    release.approved_by = actor
    release.approved_at = timezone.now()
    release.instructed_at = timezone.now()
    release.provider_instruction_id = provider_instruction_id or adapter_reference
    release.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at",
            "instructed_at",
            "provider_instruction_id",
            "updated_at",
        ]
    )
    escrow.release_status = EscrowReleaseStatus.SENT_TO_PROVIDER
    escrow.save(update_fields=["release_status", "updated_at"])
    create_audit_log(actor, "escrow_release_sent_to_provider", release, metadata={"note": note})
    return release


@db_transaction.atomic
def confirm_release(
    *, release: EscrowRelease, actor, provider_reference: str, settlement=None
) -> EscrowRelease:
    release = EscrowRelease.objects.select_for_update().select_related("escrow").get(id=release.id)
    escrow = EscrowTransaction.objects.select_for_update().get(id=release.escrow_id)
    if not can_manage_escrow(actor, escrow.transaction):
        raise ValidationError("You are not allowed to confirm this release.")
    provider_reference = (provider_reference or "").strip()
    if not provider_reference:
        raise ValidationError("Provider settlement reference is required.")
    if release.status not in {EscrowReleaseStatus.SENT_TO_PROVIDER, EscrowReleaseStatus.APPROVED}:
        raise ValidationError("Release has not been sent to provider.")
    release.status = EscrowReleaseStatus.CONFIRMED
    release.provider_reference = provider_reference
    release.confirmed_at = timezone.now()
    release.save(update_fields=["status", "provider_reference", "confirmed_at", "updated_at"])
    escrow.status = EscrowStatus.RELEASED
    escrow.release_status = EscrowReleaseStatus.CONFIRMED
    escrow.released_at = release.confirmed_at
    escrow.closed_at = release.confirmed_at
    escrow.save(
        update_fields=["status", "release_status", "released_at", "closed_at", "updated_at"]
    )
    create_audit_log(
        actor,
        "escrow_release_confirmed",
        release,
        metadata={"provider_reference": provider_reference},
    )
    _notify_participants(
        escrow,
        title="Escrow release confirmed",
        body="The escrow partner has confirmed settlement for this transaction.",
        actor=actor,
    )
    return release


@db_transaction.atomic
def request_refund(
    *, escrow: EscrowTransaction, actor, amount=None, reason: str = "", idempotency_key: str = ""
) -> EscrowRefund:
    escrow = EscrowTransaction.objects.select_for_update().get(id=escrow.id)
    if not can_manage_escrow(actor, escrow.transaction) and actor.id != escrow.transaction.buyer_id:
        raise ValidationError("You are not allowed to request refund for this escrow.")
    if not reason.strip():
        raise ValidationError("Refund reason is required.")
    amount = _money(amount or escrow.confirmed_funded_amount)
    if amount <= 0 or amount > escrow.confirmed_funded_amount:
        raise ValidationError("Refund amount must be funded and greater than zero.")
    if idempotency_key:
        existing = EscrowRefund.objects.filter(
            escrow=escrow,
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return existing
    refund = EscrowRefund.objects.create(
        escrow=escrow,
        amount=amount,
        currency=escrow.currency,
        requested_by=actor,
        reason=reason,
        idempotency_key=idempotency_key,
    )
    escrow.status = EscrowStatus.REFUND_PENDING
    escrow.refund_status = EscrowRefundStatus.REQUESTED
    escrow.save(update_fields=["status", "refund_status", "updated_at"])
    create_audit_log(actor, "escrow_refund_requested", refund, metadata={"amount": str(amount)})
    return refund


@db_transaction.atomic
def approve_refund(
    *, refund: EscrowRefund, actor, provider_instruction_id: str = "", note: str = ""
) -> EscrowRefund:
    refund = EscrowRefund.objects.select_for_update().select_related("escrow").get(id=refund.id)
    escrow = EscrowTransaction.objects.select_for_update().get(id=refund.escrow_id)
    if not can_manage_escrow(actor, escrow.transaction):
        raise ValidationError("You are not allowed to approve this refund.")
    if refund.status != EscrowRefundStatus.REQUESTED:
        raise ValidationError("Only requested refunds can be approved.")
    adapter_reference = get_escrow_provider_adapter(escrow.provider).request_refund(refund=refund)
    refund.status = EscrowRefundStatus.SENT_TO_PROVIDER
    refund.approved_by = actor
    refund.approved_at = timezone.now()
    refund.instructed_at = timezone.now()
    refund.provider_instruction_id = provider_instruction_id or adapter_reference
    refund.save(
        update_fields=[
            "status",
            "approved_by",
            "approved_at",
            "instructed_at",
            "provider_instruction_id",
            "updated_at",
        ]
    )
    escrow.refund_status = EscrowRefundStatus.SENT_TO_PROVIDER
    escrow.save(update_fields=["refund_status", "updated_at"])
    create_audit_log(actor, "escrow_refund_sent_to_provider", refund, metadata={"note": note})
    return refund


@db_transaction.atomic
def confirm_refund(*, refund: EscrowRefund, actor, provider_reference: str) -> EscrowRefund:
    refund = EscrowRefund.objects.select_for_update().select_related("escrow").get(id=refund.id)
    escrow = EscrowTransaction.objects.select_for_update().get(id=refund.escrow_id)
    if not can_manage_escrow(actor, escrow.transaction):
        raise ValidationError("You are not allowed to confirm this refund.")
    provider_reference = (provider_reference or "").strip()
    if not provider_reference:
        raise ValidationError("Provider refund reference is required.")
    if refund.status not in {EscrowRefundStatus.SENT_TO_PROVIDER, EscrowRefundStatus.APPROVED}:
        raise ValidationError("Refund has not been sent to provider.")
    refund.status = EscrowRefundStatus.CONFIRMED
    refund.provider_reference = provider_reference
    refund.confirmed_at = timezone.now()
    refund.save(update_fields=["status", "provider_reference", "confirmed_at", "updated_at"])
    escrow.status = EscrowStatus.REFUNDED
    escrow.refund_status = EscrowRefundStatus.CONFIRMED
    escrow.refunded_at = refund.confirmed_at
    escrow.closed_at = refund.confirmed_at
    escrow.save(update_fields=["status", "refund_status", "refunded_at", "closed_at", "updated_at"])
    create_audit_log(
        actor,
        "escrow_refund_confirmed",
        refund,
        metadata={"provider_reference": provider_reference},
    )
    return refund


@db_transaction.atomic
def record_settlement(
    *,
    escrow: EscrowTransaction,
    actor,
    provider_settlement_reference: str,
    gross_amount,
    seller_amount,
    platform_fee_amount=Decimal("0"),
    provider_fee_amount=Decimal("0"),
    settled_at=None,
    allocations: list[dict] | None = None,
) -> EscrowSettlement:
    escrow = EscrowTransaction.objects.select_for_update().get(id=escrow.id)
    if not can_manage_escrow(actor, escrow.transaction):
        raise ValidationError("You are not allowed to record settlement for this escrow.")
    provider_settlement_reference = (provider_settlement_reference or "").strip()
    if not provider_settlement_reference:
        raise ValidationError("Provider settlement reference is required.")
    settlement = EscrowSettlement.objects.create(
        escrow=escrow,
        provider_settlement_reference=provider_settlement_reference,
        gross_amount=_money(gross_amount),
        seller_amount=_money(seller_amount),
        platform_fee_amount=_money(platform_fee_amount),
        provider_fee_amount=_money(provider_fee_amount),
        currency=escrow.currency,
        settled_at=settled_at or timezone.now(),
        recorded_by=actor,
    )
    for allocation in allocations or []:
        EscrowSettlementAllocation.objects.create(
            settlement=settlement,
            allocation_type=allocation["allocation_type"],
            recipient_label=allocation["recipient_label"],
            amount=_money(allocation["amount"]),
            currency=allocation.get("currency") or escrow.currency,
            provider_reference=allocation.get("provider_reference", ""),
        )
    escrow.fee_status = (
        EscrowFeeStatus.SETTLED
        if settlement.platform_fee_amount > 0
        else escrow.fee_status
    )
    escrow.save(update_fields=["fee_status", "updated_at"])
    create_audit_log(actor, "escrow_settlement_confirmed", settlement, metadata={})
    return settlement


@db_transaction.atomic
def reconcile_escrow(
    *,
    escrow: EscrowTransaction,
    actor,
    provider_amount,
    provider_status: str,
    mismatch_details: str = "",
) -> EscrowReconciliationRecord:
    escrow = EscrowTransaction.objects.select_for_update().get(id=escrow.id)
    if not can_manage_escrow(actor, escrow.transaction):
        raise ValidationError("You are not allowed to reconcile this escrow.")
    provider_amount = _money(provider_amount)
    matched = (
        provider_amount == _money(escrow.confirmed_funded_amount)
        and provider_status == escrow.status
    )
    record_status = (
        EscrowReconciliationRecordStatus.MATCHED
        if matched
        else EscrowReconciliationRecordStatus.MISMATCH
    )
    record = EscrowReconciliationRecord.objects.create(
        escrow=escrow,
        status=record_status,
        expected_amount=escrow.confirmed_funded_amount,
        provider_amount=provider_amount,
        expected_status=escrow.status,
        provider_status=provider_status,
        mismatch_details=mismatch_details,
        checked_at=timezone.now(),
    )
    escrow.reconciliation_status = (
        EscrowReconciliationStatus.MATCHED
        if matched
        else EscrowReconciliationStatus.MISMATCH
    )
    escrow.save(update_fields=["reconciliation_status", "updated_at"])
    create_audit_log(
        actor,
        "escrow_reconciliation_checked",
        record,
        metadata={"status": record_status},
    )
    return record


@db_transaction.atomic
def record_provider_webhook(
    *,
    provider: EscrowProvider,
    body: bytes,
    signature: str | None,
    provider_event_id: str,
    event_type: str,
    related_escrow: EscrowTransaction | None = None,
) -> tuple[ProviderWebhookEvent, bool]:
    provider_event_id = (provider_event_id or "").strip()
    if not provider_event_id:
        raise ValidationError("Provider event id is required.")
    payload_hash = hashlib.sha256(body).hexdigest()
    adapter = get_escrow_provider_adapter(provider)
    signature_valid = adapter.verify_webhook(body=body, signature=signature)
    signature_status = (
        ProviderWebhookSignatureStatus.VALID
        if signature_valid
        else ProviderWebhookSignatureStatus.INVALID
    )
    existing = ProviderWebhookEvent.objects.filter(
        provider=provider,
        provider_event_id=provider_event_id,
    ).first()
    if existing:
        existing.processing_status = ProviderWebhookProcessingStatus.DUPLICATE
        existing.save(update_fields=["processing_status", "updated_at"])
        return existing, False
    event = ProviderWebhookEvent.objects.create(
        provider=provider,
        related_escrow=related_escrow,
        provider_event_id=provider_event_id,
        event_type=event_type,
        signature_status=signature_status,
        payload_hash=payload_hash,
        processing_status=(
            ProviderWebhookProcessingStatus.RECEIVED
            if signature_valid
            else ProviderWebhookProcessingStatus.FAILED
        ),
        received_at=timezone.now(),
        last_error="" if signature_valid else "invalid_signature",
    )
    return event, True


def _notify_participants(escrow: EscrowTransaction, *, title: str, body: str, actor=None) -> None:
    recipients = {escrow.transaction.buyer, escrow.transaction.owner}
    for recipient in recipients:
        create_notification(
            recipient=recipient,
            notification_type=NotificationType.SYSTEM,
            title=title,
            body=body,
            related_entity=escrow,
            action_url=f"/dashboard/transactions/{escrow.transaction_id}/escrow",
            force=True,
        )
