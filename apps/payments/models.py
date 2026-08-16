from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.common.models import BaseModel
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
    FinancingDocumentType,
    FinancingIntegrationMode,
    FinancingOfferStatus,
    FinancingPartnerStatus,
    FinancingPartnerSubmissionStatus,
    FinancingPartnerType,
    FinancingProductStatus,
    FinancingProductType,
    FinancingTimelineVisibility,
    MilestoneStatus,
    ProviderWebhookProcessingStatus,
    ProviderWebhookSignatureStatus,
    TransactionStatus,
)
from apps.payments.storage import get_financing_document_storage, get_payment_proof_storage
from apps.payments.validators import validate_financing_document, validate_payment_proof


class Transaction(BaseModel):
    """Proof-tracking record for a property transaction.

    This is recordkeeping only -- it does NOT represent escrow, custody,
    or payment processing. No status or field on this model or its
    related PaymentMilestone/PaymentProof should ever be presented as a
    guarantee of funds moved or held by RealityNG.
    """

    VALID_TRANSITIONS: dict[str, set[str]] = {
        TransactionStatus.DRAFT: {TransactionStatus.ACTIVE, TransactionStatus.CANCELLED},
        TransactionStatus.ACTIVE: {
            TransactionStatus.COMPLETED,
            TransactionStatus.CANCELLED,
            TransactionStatus.DISPUTED,
        },
        TransactionStatus.DISPUTED: {
            TransactionStatus.ACTIVE,
            TransactionStatus.CANCELLED,
        },
        TransactionStatus.COMPLETED: set(),
        TransactionStatus.CANCELLED: set(),
    }

    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transactions_as_buyer",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transactions_as_owner",
    )
    application = models.ForeignKey(
        "properties.RentalApplication",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    status = models.CharField(
        max_length=32,
        choices=TransactionStatus.choices,
        default=TransactionStatus.DRAFT,
        db_index=True,
    )
    currency = models.CharField(max_length=3, default="NGN")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["buyer", "status", "created_at"]),
            models.Index(fields=["owner", "status", "created_at"]),
            models.Index(fields=["property", "status"]),
            models.Index(fields=["application", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=~Q(buyer=models.F("owner")),
                name="transaction_buyer_owner_different",
            ),
            models.UniqueConstraint(
                fields=["application"],
                condition=Q(application__isnull=False, deleted_at__isnull=True),
                name="unique_live_transaction_per_application",
            ),
        ]

    def __str__(self) -> str:
        return f"Transaction {self.id} ({self.status})"

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    def clean(self) -> None:
        if self.buyer_id and self.owner_id and self.buyer_id == self.owner_id:
            raise ValidationError("Buyer and owner cannot be the same user.")


class PaymentMilestone(BaseModel):
    """A single expected payment within a Transaction (e.g. deposit, rent)."""

    VALID_TRANSITIONS: dict[str, set[str]] = {
        MilestoneStatus.PENDING: {MilestoneStatus.PROOF_UPLOADED, MilestoneStatus.CANCELLED},
        MilestoneStatus.PROOF_UPLOADED: {
            MilestoneStatus.UNDER_REVIEW,
            MilestoneStatus.CANCELLED,
        },
        MilestoneStatus.UNDER_REVIEW: {
            MilestoneStatus.ACCEPTED,
            MilestoneStatus.REJECTED,
            MilestoneStatus.DISPUTED,
        },
        MilestoneStatus.REJECTED: {
            MilestoneStatus.PROOF_UPLOADED,
            MilestoneStatus.CANCELLED,
        },
        MilestoneStatus.DISPUTED: {
            MilestoneStatus.UNDER_REVIEW,
            MilestoneStatus.CANCELLED,
        },
        MilestoneStatus.ACCEPTED: set(),
        MilestoneStatus.CANCELLED: set(),
    }

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="milestones",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    due_date = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=32,
        choices=MilestoneStatus.choices,
        default=MilestoneStatus.PENDING,
        db_index=True,
    )

    class Meta:
        ordering = ["transaction", "order", "created_at"]
        indexes = [
            models.Index(fields=["transaction", "status"]),
            models.Index(fields=["transaction", "order"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(amount__gt=0),
                name="payment_milestone_amount_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.status})"

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())


class PaymentProof(BaseModel):
    """Uploaded evidence of payment for a milestone.

    Wording shown to users about this evidence must stick to "uploaded",
    "pending review", "accepted"/"rejected" -- never "payment completed",
    "escrow secured", or similar guarantee language.
    """

    milestone = models.ForeignKey(
        PaymentMilestone,
        on_delete=models.CASCADE,
        related_name="proofs",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payment_proofs",
    )
    file = models.FileField(
        upload_to="payment-proofs/%Y/%m/",
        storage=get_payment_proof_storage,
        validators=[validate_payment_proof],
    )
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    checksum = models.CharField(max_length=64, db_index=True)
    amount_claimed = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["milestone", "created_at"]),
            models.Index(fields=["uploaded_by", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(amount_claimed__gt=0),
                name="payment_proof_amount_claimed_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"Proof for {self.milestone_id} by {self.uploaded_by_id}"


class PaymentDispute(BaseModel):
    """A raised dispute over a Transaction or one of its milestones."""

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="disputes",
    )
    milestone = models.ForeignKey(
        PaymentMilestone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disputes",
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="opened_disputes",
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=DisputeStatus.choices,
        default=DisputeStatus.OPEN,
        db_index=True,
    )
    resolution_note = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="resolved_disputes",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["transaction", "status", "created_at"]),
            models.Index(fields=["opened_by", "status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Dispute {self.id} ({self.status})"


class EscrowProvider(BaseModel):
    """Escrow/custody partner metadata.

    Credentials and API secrets are intentionally not stored here. Provider
    adapters load secrets from environment/secret-management at runtime.
    """

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    status = models.CharField(
        max_length=32,
        choices=EscrowProviderStatus.choices,
        default=EscrowProviderStatus.DRAFT,
        db_index=True,
    )
    integration_mode = models.CharField(
        max_length=24,
        choices=EscrowIntegrationMode.choices,
        default=EscrowIntegrationMode.MANUAL,
    )
    supports_partial_funding = models.BooleanField(default=False)
    supports_partial_release = models.BooleanField(default=False)
    supports_refunds = models.BooleanField(default=True)
    supports_webhooks = models.BooleanField(default=False)
    supports_reconciliation = models.BooleanField(default=True)
    supported_currencies = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["status", "integration_mode"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self) -> str:
        return self.name

    def supports_currency(self, currency: str) -> bool:
        currencies = [str(item).upper() for item in (self.supported_currencies or [])]
        return not currencies or currency.upper() in currencies


class EscrowTransaction(BaseModel):
    """Provider-backed escrow orchestration attached to a Transaction.

    This model tracks RealityNG's orchestration state. It does not mean
    RealityNG holds money. Funding/release/refund authority comes from the
    provider events or audited manual provider confirmation.
    """

    VALID_TRANSITIONS: dict[str, set[str]] = {
        EscrowStatus.DRAFT: {EscrowStatus.AWAITING_PROVIDER, EscrowStatus.CANCELLED},
        EscrowStatus.AWAITING_PROVIDER: {
            EscrowStatus.AWAITING_FUNDING,
            EscrowStatus.CANCELLED,
            EscrowStatus.FAILED,
        },
        EscrowStatus.AWAITING_FUNDING: {
            EscrowStatus.PARTIALLY_FUNDED,
            EscrowStatus.FUNDED,
            EscrowStatus.DISPUTED,
            EscrowStatus.CANCELLED,
            EscrowStatus.FAILED,
        },
        EscrowStatus.PARTIALLY_FUNDED: {
            EscrowStatus.FUNDED,
            EscrowStatus.REFUND_PENDING,
            EscrowStatus.DISPUTED,
            EscrowStatus.FAILED,
        },
        EscrowStatus.FUNDED: {
            EscrowStatus.CONDITIONS_PENDING,
            EscrowStatus.RELEASE_PENDING,
            EscrowStatus.REFUND_PENDING,
            EscrowStatus.DISPUTED,
        },
        EscrowStatus.CONDITIONS_PENDING: {
            EscrowStatus.RELEASE_PENDING,
            EscrowStatus.REFUND_PENDING,
            EscrowStatus.DISPUTED,
        },
        EscrowStatus.RELEASE_PENDING: {
            EscrowStatus.RELEASED,
            EscrowStatus.DISPUTED,
            EscrowStatus.FAILED,
        },
        EscrowStatus.REFUND_PENDING: {
            EscrowStatus.REFUNDED,
            EscrowStatus.DISPUTED,
            EscrowStatus.FAILED,
        },
        EscrowStatus.DISPUTED: {
            EscrowStatus.CONDITIONS_PENDING,
            EscrowStatus.RELEASE_PENDING,
            EscrowStatus.REFUND_PENDING,
            EscrowStatus.CANCELLED,
        },
        EscrowStatus.RELEASED: set(),
        EscrowStatus.REFUNDED: set(),
        EscrowStatus.CANCELLED: set(),
        EscrowStatus.FAILED: set(),
    }

    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name="escrow",
    )
    provider = models.ForeignKey(
        EscrowProvider,
        on_delete=models.PROTECT,
        related_name="escrows",
    )
    external_reference = models.CharField(max_length=160, blank=True)
    currency = models.CharField(max_length=3)
    expected_amount = models.DecimalField(max_digits=18, decimal_places=2)
    confirmed_funded_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status = models.CharField(
        max_length=32,
        choices=EscrowStatus.choices,
        default=EscrowStatus.DRAFT,
        db_index=True,
    )
    funding_status = models.CharField(
        max_length=32,
        choices=EscrowFundingStatus.choices,
        default=EscrowFundingStatus.FUNDING_EXPECTED,
        db_index=True,
    )
    release_status = models.CharField(
        max_length=32,
        choices=EscrowReleaseStatus.choices,
        default=EscrowReleaseStatus.NOT_REQUESTED,
        db_index=True,
    )
    refund_status = models.CharField(
        max_length=32,
        choices=EscrowRefundStatus.choices,
        default=EscrowRefundStatus.NOT_REQUESTED,
        db_index=True,
    )
    reconciliation_status = models.CharField(
        max_length=32,
        choices=EscrowReconciliationStatus.choices,
        default=EscrowReconciliationStatus.NOT_CHECKED,
        db_index=True,
    )
    platform_fee_type = models.CharField(
        max_length=16,
        choices=EscrowFeeType.choices,
        default=EscrowFeeType.NONE,
    )
    platform_fee_value = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    expected_platform_fee = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    provider_fee = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    fee_status = models.CharField(
        max_length=32,
        choices=EscrowFeeStatus.choices,
        default=EscrowFeeStatus.NOT_APPLICABLE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_escrows",
    )
    funded_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "status", "created_at"]),
            models.Index(fields=["transaction", "status"]),
            models.Index(fields=["funding_status", "release_status"]),
            models.Index(fields=["reconciliation_status", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_reference"],
                condition=Q(external_reference__gt="", deleted_at__isnull=True),
                name="unique_live_escrow_provider_reference",
            ),
            models.CheckConstraint(
                check=Q(expected_amount__gt=0),
                name="escrow_expected_amount_positive",
            ),
            models.CheckConstraint(
                check=Q(confirmed_funded_amount__gte=0),
                name="escrow_confirmed_funded_amount_non_negative",
            ),
            models.CheckConstraint(
                check=Q(expected_platform_fee__gte=0, provider_fee__gte=0),
                name="escrow_fees_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"Escrow {self.id} ({self.status})"

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())


class EscrowFundingEvent(BaseModel):
    escrow = models.ForeignKey(
        EscrowTransaction,
        on_delete=models.CASCADE,
        related_name="funding_events",
    )
    provider_event_id = models.CharField(max_length=180)
    provider_reference = models.CharField(max_length=180, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3)
    event_type = models.CharField(max_length=40, choices=EscrowFundingEventType.choices)
    provider_status = models.CharField(max_length=80, blank=True)
    occurred_at = models.DateTimeField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recorded_escrow_funding_events",
    )
    raw_reference = models.CharField(max_length=220, blank=True)
    is_reconciled = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(fields=["escrow", "event_type", "occurred_at"]),
            models.Index(fields=["provider_event_id"]),
            models.Index(fields=["is_reconciled", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["escrow", "provider_event_id"],
                condition=Q(deleted_at__isnull=True),
                name="unique_live_escrow_provider_event",
            ),
            models.CheckConstraint(
                check=Q(amount__gt=0),
                name="escrow_funding_event_amount_positive",
            ),
        ]


class EscrowCondition(BaseModel):
    escrow = models.ForeignKey(
        EscrowTransaction,
        on_delete=models.CASCADE,
        related_name="conditions",
    )
    condition_type = models.CharField(max_length=64, choices=EscrowConditionType.choices)
    status = models.CharField(
        max_length=24,
        choices=EscrowConditionStatus.choices,
        default=EscrowConditionStatus.PENDING,
        db_index=True,
    )
    description = models.TextField(blank=True)
    required = models.BooleanField(default=True)
    inspection_request = models.ForeignKey(
        "inspections.InspectionRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escrow_conditions",
    )
    construction_milestone = models.ForeignKey(
        "construction.ConstructionMilestone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="escrow_conditions",
    )
    satisfied_at = models.DateTimeField(null=True, blank=True)
    satisfied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="satisfied_escrow_conditions",
    )
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["escrow", "status", "required"]),
            models.Index(fields=["condition_type", "status"]),
        ]


class EscrowRelease(BaseModel):
    escrow = models.ForeignKey(
        EscrowTransaction,
        on_delete=models.CASCADE,
        related_name="releases",
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(
        max_length=32,
        choices=EscrowReleaseStatus.choices,
        default=EscrowReleaseStatus.REQUESTED,
        db_index=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_escrow_releases",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_escrow_releases",
    )
    provider_instruction_id = models.CharField(max_length=180, blank=True)
    provider_reference = models.CharField(max_length=180, blank=True)
    idempotency_key = models.CharField(max_length=120, blank=True)
    reason = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    instructed_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["escrow", "status", "created_at"]),
            models.Index(fields=["provider_instruction_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["escrow", "idempotency_key"],
                condition=Q(idempotency_key__gt="", deleted_at__isnull=True),
                name="unique_live_escrow_release_idempotency",
            ),
            models.CheckConstraint(
                check=Q(amount__gt=0),
                name="escrow_release_amount_positive",
            ),
        ]


class EscrowRefund(BaseModel):
    escrow = models.ForeignKey(
        EscrowTransaction,
        on_delete=models.CASCADE,
        related_name="refunds",
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(
        max_length=32,
        choices=EscrowRefundStatus.choices,
        default=EscrowRefundStatus.REQUESTED,
        db_index=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_escrow_refunds",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_escrow_refunds",
    )
    provider_instruction_id = models.CharField(max_length=180, blank=True)
    provider_reference = models.CharField(max_length=180, blank=True)
    idempotency_key = models.CharField(max_length=120, blank=True)
    reason = models.TextField()
    approved_at = models.DateTimeField(null=True, blank=True)
    instructed_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["escrow", "status", "created_at"]),
            models.Index(fields=["provider_instruction_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["escrow", "idempotency_key"],
                condition=Q(idempotency_key__gt="", deleted_at__isnull=True),
                name="unique_live_escrow_refund_idempotency",
            ),
            models.CheckConstraint(
                check=Q(amount__gt=0),
                name="escrow_refund_amount_positive",
            ),
        ]


class EscrowSettlement(BaseModel):
    escrow = models.ForeignKey(
        EscrowTransaction,
        on_delete=models.CASCADE,
        related_name="settlements",
    )
    provider_settlement_reference = models.CharField(max_length=180)
    gross_amount = models.DecimalField(max_digits=18, decimal_places=2)
    seller_amount = models.DecimalField(max_digits=18, decimal_places=2)
    platform_fee_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    provider_fee_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=32, default="confirmed", db_index=True)
    settled_at = models.DateTimeField()
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recorded_escrow_settlements",
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-settled_at", "-created_at"]
        indexes = [
            models.Index(fields=["escrow", "status", "settled_at"]),
            models.Index(fields=["provider_settlement_reference"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["escrow", "provider_settlement_reference"],
                condition=Q(deleted_at__isnull=True),
                name="unique_live_escrow_settlement_reference",
            ),
            models.CheckConstraint(
                check=Q(gross_amount__gt=0),
                name="escrow_settlement_gross_amount_positive",
            ),
            models.CheckConstraint(
                check=Q(
                    seller_amount__gte=0,
                    platform_fee_amount__gte=0,
                    provider_fee_amount__gte=0,
                ),
                name="escrow_settlement_allocations_non_negative",
            ),
        ]


class EscrowSettlementAllocation(BaseModel):
    settlement = models.ForeignKey(
        EscrowSettlement,
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    allocation_type = models.CharField(max_length=40)
    recipient_label = models.CharField(max_length=160)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3)
    provider_reference = models.CharField(max_length=180, blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                check=Q(amount__gte=0),
                name="escrow_settlement_allocation_amount_non_negative",
            ),
        ]


class ProviderWebhookEvent(BaseModel):
    provider = models.ForeignKey(
        EscrowProvider,
        on_delete=models.PROTECT,
        related_name="webhook_events",
    )
    related_escrow = models.ForeignKey(
        EscrowTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="webhook_events",
    )
    provider_event_id = models.CharField(max_length=180)
    event_type = models.CharField(max_length=80)
    signature_status = models.CharField(
        max_length=24,
        choices=ProviderWebhookSignatureStatus.choices,
        default=ProviderWebhookSignatureStatus.NOT_CONFIGURED,
    )
    payload_hash = models.CharField(max_length=64)
    processing_status = models.CharField(
        max_length=24,
        choices=ProviderWebhookProcessingStatus.choices,
        default=ProviderWebhookProcessingStatus.RECEIVED,
        db_index=True,
    )
    received_at = models.DateTimeField()
    processed_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["provider", "event_type", "received_at"]),
            models.Index(fields=["processing_status", "received_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_event_id"],
                condition=Q(deleted_at__isnull=True),
                name="unique_live_escrow_webhook_event",
            ),
        ]


class EscrowReconciliationRecord(BaseModel):
    escrow = models.ForeignKey(
        EscrowTransaction,
        on_delete=models.CASCADE,
        related_name="reconciliation_records",
    )
    status = models.CharField(
        max_length=24,
        choices=EscrowReconciliationRecordStatus.choices,
        default=EscrowReconciliationRecordStatus.PENDING_REVIEW,
        db_index=True,
    )
    expected_amount = models.DecimalField(max_digits=18, decimal_places=2)
    provider_amount = models.DecimalField(max_digits=18, decimal_places=2)
    expected_status = models.CharField(max_length=40)
    provider_status = models.CharField(max_length=40)
    mismatch_details = models.TextField(blank=True)
    checked_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="resolved_escrow_reconciliations",
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-checked_at"]
        indexes = [
            models.Index(fields=["escrow", "status", "checked_at"]),
            models.Index(fields=["status", "checked_at"]),
        ]


def financing_document_upload_to(instance: FinancingDocument, filename: str) -> str:
    return f"financing/{instance.application_id}/documents/{filename}"


class FinancingPartner(BaseModel):
    """Approved financial partner metadata.

    API credentials and underwriting rules are deliberately not stored here.
    RealityNG orchestrates applications; the partner owns credit decisions.
    """

    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True)
    status = models.CharField(
        max_length=32,
        choices=FinancingPartnerStatus.choices,
        default=FinancingPartnerStatus.DRAFT,
        db_index=True,
    )
    partner_type = models.CharField(
        max_length=32,
        choices=FinancingPartnerType.choices,
        default=FinancingPartnerType.MANUAL,
    )
    integration_mode = models.CharField(
        max_length=24,
        choices=FinancingIntegrationMode.choices,
        default=FinancingIntegrationMode.MANUAL,
    )
    supported_products = models.JSONField(default=list, blank=True)
    supported_states = models.JSONField(default=list, blank=True)
    minimum_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    maximum_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    contact_policy = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["status", "partner_type"]),
            models.Index(fields=["integration_mode", "status"]),
            models.Index(fields=["slug"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(minimum_amount__gte=0, maximum_amount__gte=0),
                name="financing_partner_amounts_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def supports_product_type(self, product_type: str) -> bool:
        products = [str(item) for item in (self.supported_products or [])]
        return not products or product_type in products

    def supports_state(self, state: str) -> bool:
        states = [str(item).lower() for item in (self.supported_states or [])]
        return not states or state.lower() in states


class FinancingProduct(BaseModel):
    partner = models.ForeignKey(
        FinancingPartner,
        on_delete=models.PROTECT,
        related_name="products",
    )
    name = models.CharField(max_length=180)
    product_type = models.CharField(max_length=32, choices=FinancingProductType.choices)
    status = models.CharField(
        max_length=24,
        choices=FinancingProductStatus.choices,
        default=FinancingProductStatus.DRAFT,
        db_index=True,
    )
    currency = models.CharField(max_length=3, default="NGN")
    minimum_amount = models.DecimalField(max_digits=18, decimal_places=2)
    maximum_amount = models.DecimalField(max_digits=18, decimal_places=2)
    minimum_tenor_months = models.PositiveSmallIntegerField(default=1)
    maximum_tenor_months = models.PositiveSmallIntegerField(default=24)
    requires_property = models.BooleanField(default=True)
    requires_income_documents = models.BooleanField(default=True)
    requires_identity_verification = models.BooleanField(default=True)
    requires_bank_statement = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["product_type", "name"]
        indexes = [
            models.Index(fields=["status", "product_type"]),
            models.Index(fields=["partner", "status"]),
            models.Index(fields=["currency", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(minimum_amount__gt=0, maximum_amount__gte=models.F("minimum_amount")),
                name="financing_product_amount_range_valid",
            ),
            models.CheckConstraint(
                check=Q(maximum_tenor_months__gte=models.F("minimum_tenor_months")),
                name="financing_product_tenor_range_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.product_type})"


class FinancingApplication(BaseModel):
    VALID_TRANSITIONS: dict[str, set[str]] = {
        FinancingApplicationStatus.DRAFT: {
            FinancingApplicationStatus.SUBMITTED,
            FinancingApplicationStatus.CANCELLED,
        },
        FinancingApplicationStatus.SUBMITTED: {
            FinancingApplicationStatus.UNDER_REVIEW,
            FinancingApplicationStatus.MORE_INFORMATION_REQUESTED,
            FinancingApplicationStatus.REJECTED,
            FinancingApplicationStatus.CANCELLED,
        },
        FinancingApplicationStatus.UNDER_REVIEW: {
            FinancingApplicationStatus.PARTNER_REVIEW,
            FinancingApplicationStatus.MORE_INFORMATION_REQUESTED,
            FinancingApplicationStatus.REJECTED,
            FinancingApplicationStatus.CANCELLED,
        },
        FinancingApplicationStatus.PARTNER_REVIEW: {
            FinancingApplicationStatus.OFFER_RECEIVED,
            FinancingApplicationStatus.MORE_INFORMATION_REQUESTED,
            FinancingApplicationStatus.REJECTED,
            FinancingApplicationStatus.EXPIRED,
        },
        FinancingApplicationStatus.MORE_INFORMATION_REQUESTED: {
            FinancingApplicationStatus.SUBMITTED,
            FinancingApplicationStatus.CANCELLED,
        },
        FinancingApplicationStatus.OFFER_RECEIVED: {
            FinancingApplicationStatus.OFFER_ACCEPTED,
            FinancingApplicationStatus.OFFER_DECLINED,
            FinancingApplicationStatus.EXPIRED,
        },
        FinancingApplicationStatus.OFFER_ACCEPTED: set(),
        FinancingApplicationStatus.OFFER_DECLINED: set(),
        FinancingApplicationStatus.REJECTED: set(),
        FinancingApplicationStatus.CANCELLED: set(),
        FinancingApplicationStatus.EXPIRED: set(),
    }

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="financing_applications",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="financing_applications",
    )
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financing_applications",
    )
    product = models.ForeignKey(
        FinancingProduct,
        on_delete=models.PROTECT,
        related_name="applications",
    )
    partner = models.ForeignKey(
        FinancingPartner,
        on_delete=models.PROTECT,
        related_name="applications",
    )
    application_reference = models.CharField(max_length=80, unique=True)
    status = models.CharField(
        max_length=40,
        choices=FinancingApplicationStatus.choices,
        default=FinancingApplicationStatus.DRAFT,
        db_index=True,
    )
    requested_amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    purpose = models.TextField()
    preferred_tenor_months = models.PositiveSmallIntegerField()
    employment_status = models.CharField(max_length=80)
    monthly_income_band = models.CharField(max_length=80)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=120, blank=True)
    consent_status = models.CharField(
        max_length=24,
        choices=FinancingConsentStatus.choices,
        default=FinancingConsentStatus.NOT_GRANTED,
        db_index=True,
    )
    applicant_message = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    partner_status = models.CharField(max_length=80, blank=True)
    partner_reference = models.CharField(max_length=160, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    partner_submitted_at = models.DateTimeField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["applicant", "status", "created_at"]),
            models.Index(fields=["partner", "status", "created_at"]),
            models.Index(fields=["product", "status"]),
            models.Index(fields=["property", "status"]),
            models.Index(fields=["transaction", "status"]),
            models.Index(fields=["state", "city", "status"]),
            models.Index(fields=["application_reference"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=Q(requested_amount__gt=0),
                name="financing_application_amount_positive",
            ),
            models.CheckConstraint(
                check=Q(preferred_tenor_months__gt=0),
                name="financing_application_tenor_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.application_reference} ({self.status})"

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())


class FinancingConsent(BaseModel):
    application = models.ForeignKey(
        FinancingApplication,
        on_delete=models.CASCADE,
        related_name="consents",
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="financing_consents",
    )
    scope = models.CharField(max_length=200)
    accepted_terms_version = models.CharField(max_length=40)
    consented_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-consented_at"]
        indexes = [
            models.Index(fields=["application", "consented_at"]),
            models.Index(fields=["applicant", "consented_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "applicant", "accepted_terms_version"],
                condition=Q(deleted_at__isnull=True, revoked_at__isnull=True),
                name="unique_active_financing_consent_per_terms",
            ),
        ]


class FinancingDocumentRequirement(BaseModel):
    product = models.ForeignKey(
        FinancingProduct,
        on_delete=models.CASCADE,
        related_name="document_requirements",
    )
    document_type = models.CharField(max_length=40, choices=FinancingDocumentType.choices)
    required = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    allowed_mime_types = models.JSONField(default=list, blank=True)
    max_size_mb = models.PositiveSmallIntegerField(default=10)

    class Meta:
        ordering = ["product", "document_type"]
        indexes = [models.Index(fields=["product", "required"])]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "document_type"],
                condition=Q(deleted_at__isnull=True),
                name="unique_live_financing_requirement_per_type",
            ),
        ]


class FinancingDocument(BaseModel):
    application = models.ForeignKey(
        FinancingApplication,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="financing_documents",
    )
    document_type = models.CharField(max_length=40, choices=FinancingDocumentType.choices)
    file = models.FileField(
        upload_to=financing_document_upload_to,
        storage=get_financing_document_storage,
        validators=[validate_financing_document],
    )
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()
    checksum = models.CharField(max_length=64, db_index=True)
    status = models.CharField(
        max_length=32,
        choices=FinancingDocumentStatus.choices,
        default=FinancingDocumentStatus.UPLOADED,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_financing_documents",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["application", "document_type", "status"]),
            models.Index(fields=["uploaded_by", "created_at"]),
            models.Index(fields=["checksum"]),
        ]


class FinancingPartnerSubmission(BaseModel):
    application = models.ForeignKey(
        FinancingApplication,
        on_delete=models.CASCADE,
        related_name="partner_submissions",
    )
    partner = models.ForeignKey(
        FinancingPartner,
        on_delete=models.PROTECT,
        related_name="financing_submissions",
    )
    submission_reference = models.CharField(max_length=160)
    status = models.CharField(
        max_length=32,
        choices=FinancingPartnerSubmissionStatus.choices,
        default=FinancingPartnerSubmissionStatus.PENDING,
        db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    response_received_at = models.DateTimeField(null=True, blank=True)
    payload_hash = models.CharField(max_length=64, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["application", "status"]),
            models.Index(fields=["partner", "status", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["partner", "submission_reference"],
                condition=Q(deleted_at__isnull=True),
                name="unique_live_financing_partner_submission_ref",
            ),
        ]


class FinancingOffer(BaseModel):
    application = models.ForeignKey(
        FinancingApplication,
        on_delete=models.CASCADE,
        related_name="offers",
    )
    partner = models.ForeignKey(
        FinancingPartner,
        on_delete=models.PROTECT,
        related_name="financing_offers",
    )
    offer_reference = models.CharField(max_length=160)
    status = models.CharField(
        max_length=24,
        choices=FinancingOfferStatus.choices,
        default=FinancingOfferStatus.PENDING,
        db_index=True,
    )
    approved_amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3)
    tenor_months = models.PositiveSmallIntegerField()
    interest_rate_display = models.CharField(max_length=120, blank=True)
    fees_display = models.CharField(max_length=200, blank=True)
    monthly_payment_display = models.CharField(max_length=120, blank=True)
    partner_terms_summary = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["application", "status", "created_at"]),
            models.Index(fields=["partner", "status"]),
            models.Index(fields=["offer_reference"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["partner", "offer_reference"],
                condition=Q(deleted_at__isnull=True),
                name="unique_live_financing_offer_reference",
            ),
            models.CheckConstraint(
                check=Q(approved_amount__gt=0),
                name="financing_offer_amount_positive",
            ),
        ]


class FinancingTimelineEvent(BaseModel):
    application = models.ForeignKey(
        FinancingApplication,
        on_delete=models.CASCADE,
        related_name="timeline_events",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="financing_timeline_events",
    )
    event_type = models.CharField(max_length=80)
    message = models.TextField()
    visibility = models.CharField(
        max_length=20,
        choices=FinancingTimelineVisibility.choices,
        default=FinancingTimelineVisibility.APPLICANT,
        db_index=True,
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["application", "visibility", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]
