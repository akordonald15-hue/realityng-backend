from __future__ import annotations

from django.db import models


class VerificationStatus(models.TextChoices):
    NOT_SUBMITTED = "not_submitted", "Not Submitted"
    PENDING = "pending", "Pending"
    UNDER_REVIEW = "under_review", "Under Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    NEEDS_MORE_INFO = "needs_more_information", "Needs More Information"
    EXPIRED = "expired", "Expired"
    SUSPENDED = "suspended", "Suspended"


class VerificationType(models.TextChoices):
    AGENT = "agent", "Agent"
    LANDLORD = "landlord", "Landlord"
    ARTISAN = "artisan", "Artisan"
    IDENTITY = "identity", "Identity"
    PROPERTY_OWNERSHIP = "property_ownership", "Property Ownership"
    PROPERTY_LISTING = "property_listing", "Property Listing"


ACTIVE_VERIFICATION_STATUSES = [
    VerificationStatus.PENDING,
    VerificationStatus.UNDER_REVIEW,
    VerificationStatus.NEEDS_MORE_INFO,
    VerificationStatus.APPROVED,
    VerificationStatus.SUSPENDED,
  ]
