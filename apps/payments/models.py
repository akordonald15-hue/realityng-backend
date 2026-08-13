from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.common.models import BaseModel
from apps.payments.choices import DisputeStatus, MilestoneStatus, TransactionStatus
from apps.payments.storage import get_payment_proof_storage
from apps.payments.validators import validate_payment_proof


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
