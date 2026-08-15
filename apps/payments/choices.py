from django.db import models


class TransactionStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    DISPUTED = "disputed", "Disputed"


class MilestoneStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROOF_UPLOADED = "proof_uploaded", "Proof Uploaded"
    UNDER_REVIEW = "under_review", "Under Review"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"
    DISPUTED = "disputed", "Disputed"
    CANCELLED = "cancelled", "Cancelled"


class DisputeStatus(models.TextChoices):
    OPEN = "open", "Open"
    UNDER_REVIEW = "under_review", "Under Review"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"


class EscrowProviderStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SANDBOX = "sandbox", "Sandbox"
    ACTIVE = "active", "Active"
    DISABLED = "disabled", "Disabled"


class EscrowIntegrationMode(models.TextChoices):
    MANUAL = "manual", "Manual"
    SANDBOX = "sandbox", "Sandbox"
    API = "api", "API"


class EscrowStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    AWAITING_PROVIDER = "awaiting_provider", "Awaiting Provider"
    AWAITING_FUNDING = "awaiting_funding", "Awaiting Funding"
    PARTIALLY_FUNDED = "partially_funded", "Partially Funded"
    FUNDED = "funded", "Funded"
    CONDITIONS_PENDING = "conditions_pending", "Conditions Pending"
    RELEASE_PENDING = "release_pending", "Release Pending"
    RELEASED = "released", "Released"
    REFUND_PENDING = "refund_pending", "Refund Pending"
    REFUNDED = "refunded", "Refunded"
    DISPUTED = "disputed", "Disputed"
    CANCELLED = "cancelled", "Cancelled"
    FAILED = "failed", "Failed"


class EscrowFundingStatus(models.TextChoices):
    FUNDING_EXPECTED = "funding_expected", "Funding Expected"
    FUNDING_CLAIMED = "funding_claimed", "Funding Claimed"
    PARTIALLY_CONFIRMED = "partially_confirmed", "Partially Confirmed"
    CONFIRMED_BY_PROVIDER = "confirmed_by_provider", "Confirmed by Provider"
    REVERSED = "reversed", "Reversed"


class EscrowReleaseStatus(models.TextChoices):
    NOT_REQUESTED = "not_requested", "Not Requested"
    REQUESTED = "requested", "Requested"
    APPROVED = "approved", "Approved"
    SENT_TO_PROVIDER = "sent_to_provider", "Sent to Provider"
    CONFIRMED = "confirmed", "Confirmed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class EscrowRefundStatus(models.TextChoices):
    NOT_REQUESTED = "not_requested", "Not Requested"
    REQUESTED = "requested", "Requested"
    APPROVED = "approved", "Approved"
    SENT_TO_PROVIDER = "sent_to_provider", "Sent to Provider"
    CONFIRMED = "confirmed", "Confirmed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class EscrowReconciliationStatus(models.TextChoices):
    NOT_CHECKED = "not_checked", "Not Checked"
    MATCHED = "matched", "Matched"
    MISMATCH = "mismatch", "Mismatch"
    PENDING_REVIEW = "pending_review", "Pending Review"
    RESOLVED = "resolved", "Resolved"


class EscrowFeeType(models.TextChoices):
    NONE = "none", "None"
    PERCENTAGE = "percentage", "Percentage"
    FIXED = "fixed", "Fixed"
    HYBRID = "hybrid", "Hybrid"


class EscrowFeeStatus(models.TextChoices):
    NOT_APPLICABLE = "not_applicable", "Not Applicable"
    CALCULATED = "calculated", "Calculated"
    EXPECTED = "expected", "Expected"
    INSTRUCTED = "instructed", "Instructed"
    SETTLED = "settled", "Settled"


class EscrowFundingEventType(models.TextChoices):
    FUNDING_CONFIRMED = "funding_confirmed", "Funding Confirmed"
    PARTIAL_FUNDING_CONFIRMED = "partial_funding_confirmed", "Partial Funding Confirmed"
    FUNDING_REVERSED = "funding_reversed", "Funding Reversed"
    OVERPAYMENT = "overpayment", "Overpayment"
    UNDERPAYMENT = "underpayment", "Underpayment"


class EscrowConditionType(models.TextChoices):
    PROPERTY_VERIFIED = "property_verified", "Property Verified"
    INSPECTION_PASSED = "inspection_passed", "Inspection Passed"
    TITLE_VERIFIED = "title_verified", "Title Verified"
    BUYER_CONFIRMATION = "buyer_confirmation", "Buyer Confirmation"
    SELLER_DOCUMENTS_COMPLETE = "seller_documents_complete", "Seller Documents Complete"
    CONSTRUCTION_MILESTONE_APPROVED = (
        "construction_milestone_approved",
        "Construction Milestone Approved",
    )
    MANUAL_CONDITION = "manual_condition", "Manual Condition"


class EscrowConditionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SATISFIED = "satisfied", "Satisfied"
    FAILED = "failed", "Failed"
    WAIVED = "waived", "Waived"


class ProviderWebhookSignatureStatus(models.TextChoices):
    VALID = "valid", "Valid"
    INVALID = "invalid", "Invalid"
    NOT_CONFIGURED = "not_configured", "Not Configured"


class ProviderWebhookProcessingStatus(models.TextChoices):
    RECEIVED = "received", "Received"
    PROCESSED = "processed", "Processed"
    DUPLICATE = "duplicate", "Duplicate"
    FAILED = "failed", "Failed"


class EscrowReconciliationRecordStatus(models.TextChoices):
    MATCHED = "matched", "Matched"
    MISMATCH = "mismatch", "Mismatch"
    PENDING_REVIEW = "pending_review", "Pending Review"
    RESOLVED = "resolved", "Resolved"


class FinancingPartnerStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    DISABLED = "disabled", "Disabled"


class FinancingPartnerType(models.TextChoices):
    BANK = "bank", "Bank"
    FINTECH = "fintech", "Fintech"
    MORTGAGE_BANK = "mortgage_bank", "Mortgage Bank"
    COOPERATIVE = "cooperative", "Cooperative"
    MANUAL = "manual", "Manual Partner"


class FinancingIntegrationMode(models.TextChoices):
    MANUAL = "manual", "Manual"
    API = "api", "API"
    HYBRID = "hybrid", "Hybrid"


class FinancingProductType(models.TextChoices):
    RENT_FINANCE = "rent_finance", "Rent Finance"
    MORTGAGE = "mortgage", "Mortgage"


class FinancingProductStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    DISABLED = "disabled", "Disabled"


class FinancingApplicationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under Review"
    PARTNER_REVIEW = "partner_review", "Partner Review"
    MORE_INFORMATION_REQUESTED = (
        "more_information_requested",
        "More Information Requested",
    )
    OFFER_RECEIVED = "offer_received", "Offer Received"
    OFFER_ACCEPTED = "offer_accepted", "Offer Accepted"
    OFFER_DECLINED = "offer_declined", "Offer Declined"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"
    EXPIRED = "expired", "Expired"


class FinancingConsentStatus(models.TextChoices):
    NOT_GRANTED = "not_granted", "Not Granted"
    GRANTED = "granted", "Granted"
    REVOKED = "revoked", "Revoked"


class FinancingDocumentType(models.TextChoices):
    IDENTITY = "identity", "Identity"
    BANK_STATEMENT = "bank_statement", "Bank Statement"
    INCOME_PROOF = "income_proof", "Income Proof"
    EMPLOYMENT_LETTER = "employment_letter", "Employment Letter"
    PROPERTY_DOCUMENT = "property_document", "Property Document"
    OTHER = "other", "Other"


class FinancingDocumentStatus(models.TextChoices):
    UPLOADED = "uploaded", "Uploaded"
    UNDER_REVIEW = "under_review", "Under Review"
    ACCEPTED = "accepted", "Accepted"
    REJECTED = "rejected", "Rejected"


class FinancingPartnerSubmissionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUBMITTED = "submitted", "Submitted"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    FAILED = "failed", "Failed"


class FinancingOfferStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"
    EXPIRED = "expired", "Expired"
    WITHDRAWN = "withdrawn", "Withdrawn"


class FinancingTimelineVisibility(models.TextChoices):
    INTERNAL = "internal", "Internal"
    APPLICANT = "applicant", "Applicant"
    PARTNER = "partner", "Partner"
