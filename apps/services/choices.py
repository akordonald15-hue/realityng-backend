from django.db import models


class ProviderType(models.TextChoices):
    INDIVIDUAL = "individual", "Individual"
    COMPANY = "company", "Company"


class ProviderStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_REVIEW = "pending_review", "Pending Review"
    ACTIVE = "active", "Active"
    NEEDS_MORE_INFORMATION = "needs_more_information", "Needs More Information"
    REJECTED = "rejected", "Rejected"
    SUSPENDED = "suspended", "Suspended"
    INACTIVE = "inactive", "Inactive"
    ARCHIVED = "archived", "Archived"


class ProviderTradeStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"


class SkillLevel(models.TextChoices):
    APPRENTICE = "apprentice", "Apprentice"
    INTERMEDIATE = "intermediate", "Intermediate"
    EXPERT = "expert", "Expert"


class PortfolioImageStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PENDING_REVIEW = "pending_review", "Pending Review"
    REJECTED = "rejected", "Rejected"


class QuoteRequestStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    VIEWED = "viewed", "Viewed"
    RESPONDED = "responded", "Responded"
    CLOSED = "closed", "Closed"
    CANCELLED = "cancelled", "Cancelled"


class ServiceBookingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class ServiceReviewStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PUBLISHED = "published", "Published"
    FLAGGED = "flagged", "Flagged"
    HIDDEN = "hidden", "Hidden"
    DISPUTED = "disputed", "Disputed"
    REMOVED = "removed", "Removed"


class ServiceReviewFlagReason(models.TextChoices):
    SPAM = "spam", "Spam"
    ABUSIVE = "abusive", "Abusive"
    FALSE_INFORMATION = "false_information", "False Information"
    PRIVACY_CONCERN = "privacy_concern", "Privacy Concern"
    CONFLICT_OF_INTEREST = "conflict_of_interest", "Conflict of Interest"
    OTHER = "other", "Other"


class ServiceComplaintType(models.TextChoices):
    CUSTOMER = "customer", "Customer Complaint"
    PROVIDER = "provider", "Provider Complaint"


class ServiceComplaintCategory(models.TextChoices):
    PROVIDER_CONDUCT = "provider_conduct", "Provider Conduct"
    CUSTOMER_CONDUCT = "customer_conduct", "Customer Conduct"
    REVIEW_ABUSE = "review_abuse", "Review Abuse"
    SAFETY = "safety", "Safety"
    FRAUD = "fraud", "Fraud"
    SERVICE_QUALITY = "service_quality", "Service Quality"
    OTHER = "other", "Other"


class ServiceComplaintStatus(models.TextChoices):
    OPEN = "open", "Open"
    UNDER_REVIEW = "under_review", "Under Review"
    AWAITING_CUSTOMER = "awaiting_customer", "Awaiting Customer"
    AWAITING_PROVIDER = "awaiting_provider", "Awaiting Provider"
    RESOLVED = "resolved", "Resolved"
    REJECTED = "rejected", "Rejected"
    ESCALATED = "escalated", "Escalated"
    CLOSED = "closed", "Closed"


class ProviderSuspensionType(models.TextChoices):
    WARNING = "warning", "Warning"
    TEMPORARY = "temporary", "Temporary Suspension"
    PERMANENT = "permanent", "Permanent Suspension"


class ProviderAppealType(models.TextChoices):
    WARNING = "warning", "Warning Appeal"
    SUSPENSION = "suspension", "Suspension Appeal"


class ProviderAppealStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    REOPENED = "reopened", "Reopened"
    CLOSED = "closed", "Closed"


class PreferredContactMethod(models.TextChoices):
    PHONE = "phone", "Phone"
    EMAIL = "email", "Email"
    WHATSAPP = "whatsapp", "WhatsApp"
