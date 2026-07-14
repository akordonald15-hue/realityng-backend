from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import BaseModel, UUIDPrimaryKeyMixin
from apps.properties.models import Property
from apps.trust.choices import (
    ACTIVE_VERIFICATION_STATUSES,
    VerificationStatus,
    VerificationType,
)


class VerificationRequest(BaseModel):
    VALID_STATUS_TRANSITIONS = {
        VerificationStatus.NOT_SUBMITTED: {VerificationStatus.PENDING},
        VerificationStatus.PENDING: {
            VerificationStatus.UNDER_REVIEW,
            VerificationStatus.REJECTED,
        },
        VerificationStatus.UNDER_REVIEW: {
            VerificationStatus.APPROVED,
            VerificationStatus.REJECTED,
            VerificationStatus.NEEDS_MORE_INFO,
        },
        VerificationStatus.NEEDS_MORE_INFO: {
            VerificationStatus.UNDER_REVIEW,
            VerificationStatus.PENDING,
        },
        VerificationStatus.REJECTED: {VerificationStatus.PENDING},
        VerificationStatus.APPROVED: {
            VerificationStatus.SUSPENDED,
            VerificationStatus.EXPIRED,
        },
        VerificationStatus.SUSPENDED: {VerificationStatus.UNDER_REVIEW},
        VerificationStatus.EXPIRED: {VerificationStatus.PENDING},
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verification_requests",
    )
    verification_type = models.CharField(max_length=32, choices=VerificationType.choices)
    status = models.CharField(
        max_length=32,
        choices=VerificationStatus.choices,
        default=VerificationStatus.NOT_SUBMITTED,
    )

    business_name = models.CharField(max_length=255, blank=True)
    cac_registration_number = models.CharField(max_length=64, blank=True)
    trade_category = models.CharField(max_length=100, blank=True)
    years_experience = models.PositiveSmallIntegerField(null=True, blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    contact_address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)

    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_verifications",
    )
    rejection_reason = models.TextField(blank=True)
    review_notes = models.TextField(blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "verification_type"],
                condition=models.Q(status__in=ACTIVE_VERIFICATION_STATUSES),
                name="uniq_active_verification_per_user_type",
            ),
        ]
        indexes = [
            models.Index(fields=["verification_type", "status"]),
            models.Index(fields=["reviewer", "status"]),
            models.Index(fields=["user", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_verification_type_display()} verification for {self.user_id} ({self.status})"

    def can_transition_to(self, next_status: str) -> bool:
        return next_status in self.VALID_STATUS_TRANSITIONS.get(self.status, set())

    def transition_to(self, next_status: str) -> None:
        if next_status == self.status:
            return
        if not self.can_transition_to(next_status):
            raise ValueError(f"Verification cannot move from {self.status} to {next_status}.")
        self.status = next_status
        self.save(update_fields=["status", "updated_at"])


class VerificationDocument(UUIDPrimaryKeyMixin):
    verification_request = models.ForeignKey(
        VerificationRequest,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=64)
    file = models.FileField(upload_to="verification/%Y/%m/")
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField()
    checksum = models.CharField(max_length=64, db_index=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reviewed_status = models.CharField(
        max_length=32,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    reviewer_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["uploaded_at"]
        indexes = [
            models.Index(fields=["verification_request", "document_type"]),
            models.Index(fields=["checksum"]),
        ]

    def __str__(self) -> str:
        return f"{self.document_type} for request {self.verification_request_id}"


class PropertyVerification(BaseModel):
    VALID_STATUS_TRANSITIONS = VerificationRequest.VALID_STATUS_TRANSITIONS

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="verifications",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="submitted_property_verifications",
    )
    status = models.CharField(
        max_length=32,
        choices=VerificationStatus.choices,
        default=VerificationStatus.NOT_SUBMITTED,
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_property_verifications",
    )
    ownership_evidence = models.ForeignKey(
        VerificationDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    location_evidence = models.ForeignKey(
        VerificationDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    inspection_evidence = models.ForeignKey(
        VerificationDocument, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    verified_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["property"],
                condition=models.Q(status__in=ACTIVE_VERIFICATION_STATUSES),
                name="uniq_active_verification_per_property",
            ),
        ]
        indexes = [
            models.Index(fields=["property", "status"]),
            models.Index(fields=["reviewer", "status"]),
        ]

    def __str__(self) -> str:
        return f"Verification for property {self.property_id} ({self.status})"

    def can_transition_to(self, next_status: str) -> bool:
        return next_status in self.VALID_STATUS_TRANSITIONS.get(self.status, set())

    def transition_to(self, next_status: str) -> None:
        if next_status == self.status:
            return
        if not self.can_transition_to(next_status):
            raise ValueError(f"Property verification cannot move from {self.status} to {next_status}.")
        self.status = next_status
        self.save(update_fields=["status", "updated_at"])
