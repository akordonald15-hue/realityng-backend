from django.db import models


class InspectionType(models.TextChoices):
    GENERAL = "general", "General"
    PRE_PURCHASE = "pre_purchase", "Pre Purchase"
    PRE_RENTAL = "pre_rental", "Pre Rental"
    STRUCTURAL = "structural", "Structural"
    ELECTRICAL = "electrical", "Electrical"
    PLUMBING = "plumbing", "Plumbing"
    CONSTRUCTION_PROGRESS = "construction_progress", "Construction Progress"
    LAND_VERIFICATION = "land_verification", "Land Verification"
    COMMERCIAL = "commercial", "Commercial"
    OTHER = "other", "Other"


class InspectionRequestStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    UNDER_REVIEW = "under_review", "Under Review"
    NEEDS_MORE_INFORMATION = "needs_more_information", "Needs More Information"
    APPROVED = "approved", "Approved"
    ASSIGNED = "assigned", "Assigned"
    SCHEDULED = "scheduled", "Scheduled"
    IN_PROGRESS = "in_progress", "In Progress"
    REPORT_SUBMITTED = "report_submitted", "Report Submitted"
    REPORT_UNDER_REVIEW = "report_under_review", "Report Under Review"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    REJECTED = "rejected", "Rejected"
    EXPIRED = "expired", "Expired"


ACTIVE_INSPECTION_REQUEST_STATUSES = [
    InspectionRequestStatus.REQUESTED,
    InspectionRequestStatus.UNDER_REVIEW,
    InspectionRequestStatus.NEEDS_MORE_INFORMATION,
    InspectionRequestStatus.APPROVED,
    InspectionRequestStatus.ASSIGNED,
    InspectionRequestStatus.SCHEDULED,
    InspectionRequestStatus.IN_PROGRESS,
    InspectionRequestStatus.REPORT_SUBMITTED,
    InspectionRequestStatus.REPORT_UNDER_REVIEW,
]


class InspectionPriority(models.TextChoices):
    LOW = "low", "Low"
    NORMAL = "normal", "Normal"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class WalkthroughStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    UPLOADING = "uploading", "Uploading"
    PENDING_REVIEW = "pending_review", "Pending Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    HIDDEN = "hidden", "Hidden"
    ARCHIVED = "archived", "Archived"
    FAILED = "failed", "Failed"


class AssignmentStatus(models.TextChoices):
    ASSIGNED = "assigned", "Assigned"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"
    CANCELLED = "cancelled", "Cancelled"
    REASSIGNED = "reassigned", "Reassigned"
    COMPLETED = "completed", "Completed"


class InspectorAvailabilityStatus(models.TextChoices):
    AVAILABLE = "available", "Available"
    LIMITED = "limited", "Limited"
    UNAVAILABLE = "unavailable", "Unavailable"


class InspectorVerificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    SUSPENDED = "suspended", "Suspended"


class InspectionReportStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under Review"
    NEEDS_REVISION = "needs_revision", "Needs Revision"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    ARCHIVED = "archived", "Archived"


class InspectionCondition(models.TextChoices):
    EXCELLENT = "excellent", "Excellent"
    GOOD = "good", "Good"
    FAIR = "fair", "Fair"
    POOR = "poor", "Poor"
    CRITICAL = "critical", "Critical"
    NOT_ASSESSED = "not_assessed", "Not Assessed"


class InspectionRiskLevel(models.TextChoices):
    LOW = "low", "Low"
    MODERATE = "moderate", "Moderate"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"
    NOT_ASSESSED = "not_assessed", "Not Assessed"


class EvidenceType(models.TextChoices):
    PHOTO = "photo", "Photo"
    VIDEO = "video", "Video"
    DOCUMENT = "document", "Document"
    VOICE_NOTE = "voice_note", "Voice Note"
    OTHER = "other", "Other"


class EvidenceCategory(models.TextChoices):
    STRUCTURAL = "structural", "Structural"
    ELECTRICAL = "electrical", "Electrical"
    PLUMBING = "plumbing", "Plumbing"
    ROOFING = "roofing", "Roofing"
    SECURITY = "security", "Security"
    ENVIRONMENT = "environment", "Environment"
    INTERIOR = "interior", "Interior"
    EXTERIOR = "exterior", "Exterior"
    LAND = "land", "Land"
    DOCUMENTATION = "documentation", "Documentation"
    OTHER = "other", "Other"


class EvidenceVisibility(models.TextChoices):
    PRIVATE_INTERNAL = "private_internal", "Private Internal"
    REQUESTER_VISIBLE = "requester_visible", "Requester Visible"
    PROPERTY_OWNER_VISIBLE = "property_owner_visible", "Property Owner Visible"
    ADMIN_ONLY = "admin_only", "Admin Only"
