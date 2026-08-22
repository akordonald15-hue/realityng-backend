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

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction as db_transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

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
    FinancingApplicationStatus,
    FinancingConsentStatus,
    FinancingDocumentStatus,
    FinancingOfferStatus,
    FinancingPartnerSubmissionStatus,
    FinancingTimelineVisibility,
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
    FinancingApplication,
    FinancingConsent,
    FinancingDocument,
    FinancingDocumentRequirement,
    FinancingOffer,
    FinancingPartnerSubmission,
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
    if (
        provider.status == EscrowProviderStatus.ACTIVE
        and not settings.ESCROW_LIVE_ACTIVATION_ENABLED
    ):
        raise ValidationError(
            "Live escrow activation is disabled pending documented professional approval."
        )
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


ACTIVE_RELEASE_STATUSES = {
    EscrowReleaseStatus.REQUESTED,
    EscrowReleaseStatus.APPROVED,
    EscrowReleaseStatus.SENT_TO_PROVIDER,
}

ACTIVE_REFUND_STATUSES = {
    EscrowRefundStatus.REQUESTED,
    EscrowRefundStatus.APPROVED,
    EscrowRefundStatus.SENT_TO_PROVIDER,
}


def _has_active_release(escrow: EscrowTransaction) -> bool:
    return escrow.releases.filter(status__in=ACTIVE_RELEASE_STATUSES).exists()


def _has_active_refund(escrow: EscrowTransaction) -> bool:
    return escrow.refunds.filter(status__in=ACTIVE_REFUND_STATUSES).exists()


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
    idempotency_key = (idempotency_key or "").strip()
    if idempotency_key:
        existing = EscrowRelease.objects.filter(
            escrow=escrow,
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return existing
    if _has_active_refund(escrow):
        raise ValidationError("Escrow release is blocked while a refund is active.")
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
    idempotency_key = (idempotency_key or "").strip()
    if idempotency_key:
        existing = EscrowRefund.objects.filter(
            escrow=escrow,
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return existing
    if _has_active_release(escrow):
        raise ValidationError("Escrow refund is blocked while a release is active.")
    if escrow.status not in {
        EscrowStatus.PARTIALLY_FUNDED,
        EscrowStatus.FUNDED,
        EscrowStatus.DISPUTED,
    }:
        raise ValidationError("Escrow is not eligible for refund request.")
    amount = _money(amount or escrow.confirmed_funded_amount)
    if amount <= 0 or amount > escrow.confirmed_funded_amount:
        raise ValidationError("Refund amount must be funded and greater than zero.")
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


def create_financing_reference() -> str:
    return f"FIN-{timezone.now():%Y%m%d}-{get_random_string(8).upper()}"


def _create_financing_timeline(
    *,
    application: FinancingApplication,
    actor,
    event_type: str,
    message: str,
    visibility: str = FinancingTimelineVisibility.APPLICANT,
    metadata: dict | None = None,
):
    from apps.payments.models import FinancingTimelineEvent

    return FinancingTimelineEvent.objects.create(
        application=application,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        event_type=event_type,
        message=message,
        visibility=visibility,
        metadata=metadata or {},
    )


def can_view_financing_application(user, application: FinancingApplication) -> bool:
    return bool(user_is_admin(user) or application.applicant_id == user.id)


def can_admin_financing(user) -> bool:
    return user_is_admin(user)


@db_transaction.atomic
def create_financing_application(
    *,
    applicant,
    product,
    requested_amount,
    purpose: str,
    preferred_tenor_months: int,
    employment_status: str,
    monthly_income_band: str,
    state: str,
    city: str = "",
    prop=None,
    transaction: Transaction | None = None,
    currency: str = "NGN",
    applicant_message: str = "",
) -> FinancingApplication:
    if transaction and transaction.buyer_id != applicant.id:
        raise ValidationError("Transaction is not available.")
    if transaction and prop and transaction.property_id != prop.id:
        raise ValidationError("Transaction must belong to the selected property.")
    application = FinancingApplication.objects.create(
        applicant=applicant,
        property=prop or (transaction.property if transaction else None),
        transaction=transaction,
        product=product,
        partner=product.partner,
        application_reference=create_financing_reference(),
        requested_amount=_money(requested_amount),
        currency=currency.upper(),
        purpose=purpose,
        preferred_tenor_months=preferred_tenor_months,
        employment_status=employment_status,
        monthly_income_band=monthly_income_band,
        state=state,
        city=city,
        applicant_message=applicant_message,
    )
    _create_financing_timeline(
        application=application,
        actor=applicant,
        event_type="financing_application_created",
        message="Financing application draft created.",
    )
    create_audit_log(
        applicant,
        "financing_application_created",
        application,
        metadata={"product_id": str(product.id), "partner_id": str(product.partner_id)},
    )
    return application


@db_transaction.atomic
def update_financing_application(
    *, application: FinancingApplication, actor, **attrs
) -> FinancingApplication:
    application = FinancingApplication.objects.select_for_update().get(id=application.id)
    if application.applicant_id != actor.id:
        raise ValidationError("You cannot edit this financing application.")
    if application.status not in {
        FinancingApplicationStatus.DRAFT,
        FinancingApplicationStatus.MORE_INFORMATION_REQUESTED,
    }:
        raise ValidationError("This financing application cannot be edited.")
    for field, value in attrs.items():
        if value is not None:
            setattr(application, field, value)
    application.save(update_fields=[*attrs.keys(), "updated_at"])
    _create_financing_timeline(
        application=application,
        actor=actor,
        event_type="financing_application_updated",
        message="Financing application updated.",
    )
    create_audit_log(actor, "financing_application_updated", application, metadata={})
    return application


@db_transaction.atomic
def grant_financing_consent(
    *,
    application: FinancingApplication,
    actor,
    scope: str,
    accepted_terms_version: str,
    ip_address: str | None = None,
    user_agent: str = "",
) -> FinancingConsent:
    application = FinancingApplication.objects.select_for_update().get(id=application.id)
    if application.applicant_id != actor.id:
        raise ValidationError("You cannot consent for this financing application.")
    consent, created = FinancingConsent.objects.get_or_create(
        application=application,
        applicant=actor,
        accepted_terms_version=accepted_terms_version,
        revoked_at__isnull=True,
        defaults={
            "scope": scope,
            "consented_at": timezone.now(),
            "ip_address": ip_address,
            "user_agent": user_agent[:255],
        },
    )
    application.consent_status = FinancingConsentStatus.GRANTED
    application.save(update_fields=["consent_status", "updated_at"])
    if created:
        _create_financing_timeline(
            application=application,
            actor=actor,
            event_type="financing_consent_granted",
            message="Applicant consented to share application data with financing partners.",
        )
        create_audit_log(actor, "financing_consent_granted", consent, metadata={"scope": scope})
    return consent


def _required_financing_document_types(application: FinancingApplication) -> set[str]:
    explicit = set(
        FinancingDocumentRequirement.objects.filter(
            product=application.product,
            required=True,
        ).values_list("document_type", flat=True)
    )
    if explicit:
        return explicit
    required = {"identity"}
    if application.product.requires_income_documents:
        required.add("income_proof")
    if application.product.requires_bank_statement:
        required.add("bank_statement")
    return required


def validate_financing_submission(application: FinancingApplication) -> None:
    if application.consent_status != FinancingConsentStatus.GRANTED:
        raise ValidationError("Applicant consent is required before submission.")
    required = _required_financing_document_types(application)
    uploaded = set(
        application.documents.filter(
            status__in=[
                FinancingDocumentStatus.UPLOADED,
                FinancingDocumentStatus.UNDER_REVIEW,
                FinancingDocumentStatus.ACCEPTED,
            ]
        ).values_list("document_type", flat=True)
    )
    missing = sorted(required - uploaded)
    if missing:
        raise ValidationError(
            {"documents": f"Missing required documents: {', '.join(missing)}."}
        )


@db_transaction.atomic
def submit_financing_application(
    *, application: FinancingApplication, actor
) -> FinancingApplication:
    application = FinancingApplication.objects.select_for_update().get(id=application.id)
    if application.applicant_id != actor.id:
        raise ValidationError("You cannot submit this financing application.")
    if application.status not in {
        FinancingApplicationStatus.DRAFT,
        FinancingApplicationStatus.MORE_INFORMATION_REQUESTED,
    }:
        raise ValidationError("This financing application cannot be submitted.")
    validate_financing_submission(application)
    application.status = FinancingApplicationStatus.SUBMITTED
    application.submitted_at = timezone.now()
    application.save(update_fields=["status", "submitted_at", "updated_at"])
    _create_financing_timeline(
        application=application,
        actor=actor,
        event_type="financing_application_submitted",
        message="Financing application submitted for RealityNG review.",
    )
    create_audit_log(actor, "financing_application_submitted", application, metadata={})
    return application


@db_transaction.atomic
def upload_financing_document(
    *, application: FinancingApplication, actor, serializer
) -> FinancingDocument:
    application = FinancingApplication.objects.select_for_update().get(id=application.id)
    if application.applicant_id != actor.id:
        raise ValidationError("You cannot upload documents for this application.")
    if application.status not in {
        FinancingApplicationStatus.DRAFT,
        FinancingApplicationStatus.MORE_INFORMATION_REQUESTED,
        FinancingApplicationStatus.SUBMITTED,
    }:
        raise ValidationError("Documents cannot be uploaded for this application status.")
    document = serializer.save()
    _create_financing_timeline(
        application=application,
        actor=actor,
        event_type="financing_document_uploaded",
        message=f"{document.get_document_type_display()} document uploaded.",
    )
    create_audit_log(
        actor,
        "financing_document_uploaded",
        document,
        metadata={"application_id": str(application.id), "document_type": document.document_type},
    )
    return document


@db_transaction.atomic
def admin_transition_financing_application(
    *,
    application: FinancingApplication,
    actor,
    status: str,
    message: str = "",
    admin_notes: str = "",
) -> FinancingApplication:
    application = FinancingApplication.objects.select_for_update().get(id=application.id)
    if not can_admin_financing(actor):
        raise ValidationError("Only admins can review financing applications.")
    if status != application.status and not application.can_transition_to(status):
        raise ValidationError(f"Application cannot move from {application.status} to {status}.")
    application.status = status
    if admin_notes:
        application.admin_notes = admin_notes
    if status in {
        FinancingApplicationStatus.REJECTED,
        FinancingApplicationStatus.CANCELLED,
        FinancingApplicationStatus.EXPIRED,
    }:
        application.decision_at = timezone.now()
    application.save(update_fields=["status", "admin_notes", "decision_at", "updated_at"])
    _create_financing_timeline(
        application=application,
        actor=actor,
        event_type=f"financing_application_{status}",
        message=message or f"Application moved to {status}.",
        visibility=(
            FinancingTimelineVisibility.APPLICANT
            if status != FinancingApplicationStatus.UNDER_REVIEW
            else FinancingTimelineVisibility.INTERNAL
        ),
    )
    create_audit_log(
        actor,
        "financing_application_status_changed",
        application,
        metadata={"status": status},
    )
    return application


@db_transaction.atomic
def submit_financing_to_partner(
    *,
    application: FinancingApplication,
    actor,
    submission_reference: str,
    payload_hash: str = "",
    message: str = "",
) -> FinancingPartnerSubmission:
    if not settings.FINANCING_LIVE_ACTIVATION_ENABLED:
        raise ValidationError(
            "Financing partner activation is disabled pending documented professional approval."
        )
    application = FinancingApplication.objects.select_for_update().get(id=application.id)
    if not can_admin_financing(actor):
        raise ValidationError("Only admins can submit financing applications to partners.")
    if application.consent_status != FinancingConsentStatus.GRANTED:
        raise ValidationError("Applicant consent is required before partner submission.")
    if application.status not in {
        FinancingApplicationStatus.SUBMITTED,
        FinancingApplicationStatus.UNDER_REVIEW,
        FinancingApplicationStatus.MORE_INFORMATION_REQUESTED,
    }:
        raise ValidationError("Application is not ready for partner submission.")
    existing = application.partner_submissions.filter(
        partner=application.partner,
        submission_reference=submission_reference,
    ).first()
    if existing:
        return existing
    submission = FinancingPartnerSubmission.objects.create(
        application=application,
        partner=application.partner,
        submission_reference=submission_reference,
        status=FinancingPartnerSubmissionStatus.SUBMITTED,
        submitted_at=timezone.now(),
        payload_hash=payload_hash,
    )
    application.status = FinancingApplicationStatus.PARTNER_REVIEW
    application.partner_submitted_at = submission.submitted_at
    application.partner_reference = submission_reference
    application.partner_status = "submitted"
    application.save(
        update_fields=[
            "status", "partner_submitted_at", "partner_reference", "partner_status", "updated_at",
        ]
    )
    _create_financing_timeline(
        application=application,
        actor=actor,
        event_type="financing_partner_submission_created",
        message=message or "Application submitted to financing partner.",
    )
    create_audit_log(
        actor,
        "financing_partner_submission_created",
        submission,
        metadata={"application_id": str(application.id)},
    )
    return submission


@db_transaction.atomic
def create_financing_offer(
    *,
    application: FinancingApplication,
    actor,
    offer_reference: str,
    approved_amount,
    currency: str,
    tenor_months: int,
    interest_rate_display: str = "",
    fees_display: str = "",
    monthly_payment_display: str = "",
    partner_terms_summary: str = "",
    expires_at=None,
) -> FinancingOffer:
    application = FinancingApplication.objects.select_for_update().get(id=application.id)
    if not can_admin_financing(actor):
        raise ValidationError("Only admins can record partner offers.")
    if application.status != FinancingApplicationStatus.PARTNER_REVIEW:
        raise ValidationError("Offers can only be recorded while partner review is active.")
    offer = FinancingOffer.objects.create(
        application=application,
        partner=application.partner,
        offer_reference=offer_reference,
        status=FinancingOfferStatus.ACTIVE,
        approved_amount=_money(approved_amount),
        currency=currency.upper(),
        tenor_months=tenor_months,
        interest_rate_display=interest_rate_display,
        fees_display=fees_display,
        monthly_payment_display=monthly_payment_display,
        partner_terms_summary=partner_terms_summary,
        expires_at=expires_at,
    )
    application.status = FinancingApplicationStatus.OFFER_RECEIVED
    application.partner_status = "offer_received"
    application.decision_at = timezone.now()
    application.save(update_fields=["status", "partner_status", "decision_at", "updated_at"])
    _create_financing_timeline(
        application=application,
        actor=actor,
        event_type="financing_offer_received",
        message="A financing partner offer has been recorded.",
    )
    create_audit_log(actor, "financing_offer_received", offer, metadata={})
    return offer


@db_transaction.atomic
def accept_financing_offer(*, offer: FinancingOffer, actor) -> FinancingOffer:
    offer = FinancingOffer.objects.select_for_update().select_related("application").get(
        id=offer.id
    )
    application = FinancingApplication.objects.select_for_update().get(id=offer.application_id)
    if application.applicant_id != actor.id:
        raise ValidationError("You cannot accept this offer.")
    if offer.status != FinancingOfferStatus.ACTIVE:
        raise ValidationError("This offer is not active.")
    if offer.expires_at and offer.expires_at <= timezone.now():
        raise ValidationError("This offer has expired.")
    if application.status != FinancingApplicationStatus.OFFER_RECEIVED:
        raise ValidationError("Application is not ready for offer acceptance.")
    offer.status = FinancingOfferStatus.ACCEPTED
    offer.accepted_at = timezone.now()
    offer.save(update_fields=["status", "accepted_at", "updated_at"])
    application.status = FinancingApplicationStatus.OFFER_ACCEPTED
    application.partner_status = "offer_accepted"
    application.save(update_fields=["status", "partner_status", "updated_at"])
    application.offers.exclude(id=offer.id).filter(status=FinancingOfferStatus.ACTIVE).update(
        status=FinancingOfferStatus.WITHDRAWN,
        updated_at=timezone.now(),
    )
    _create_financing_timeline(
        application=application,
        actor=actor,
        event_type="financing_offer_accepted",
        message="Applicant accepted the partner financing offer.",
    )
    create_audit_log(actor, "financing_offer_accepted", offer, metadata={})
    return offer


@db_transaction.atomic
def decline_financing_offer(*, offer: FinancingOffer, actor) -> FinancingOffer:
    offer = FinancingOffer.objects.select_for_update().select_related("application").get(
        id=offer.id
    )
    application = FinancingApplication.objects.select_for_update().get(id=offer.application_id)
    if application.applicant_id != actor.id:
        raise ValidationError("You cannot decline this offer.")
    if offer.status != FinancingOfferStatus.ACTIVE:
        raise ValidationError("This offer is not active.")
    offer.status = FinancingOfferStatus.DECLINED
    offer.declined_at = timezone.now()
    offer.save(update_fields=["status", "declined_at", "updated_at"])
    has_active_offer = (
        application.offers.filter(status=FinancingOfferStatus.ACTIVE)
        .exclude(id=offer.id)
        .exists()
    )
    if not has_active_offer:
        application.status = FinancingApplicationStatus.OFFER_DECLINED
        application.partner_status = "offer_declined"
        application.save(update_fields=["status", "partner_status", "updated_at"])
    _create_financing_timeline(
        application=application,
        actor=actor,
        event_type="financing_offer_declined",
        message="Applicant declined a partner financing offer.",
    )
    create_audit_log(actor, "financing_offer_declined", offer, metadata={})
    return offer
