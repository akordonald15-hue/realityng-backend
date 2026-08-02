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
