from django.db import models


class ConstructionProjectType(models.TextChoices):
    NEW_BUILD = "new_build", "New Build"
    RENOVATION = "renovation", "Renovation"
    EXTENSION = "extension", "Extension"
    REMODEL = "remodel", "Remodel"
    REPAIR = "repair", "Repair"
    COMMERCIAL_DEVELOPMENT = "commercial_development", "Commercial Development"
    RESIDENTIAL_DEVELOPMENT = "residential_development", "Residential Development"
    INFRASTRUCTURE = "infrastructure", "Infrastructure"
    OTHER = "other", "Other"


class ConstructionProjectStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PLANNED = "planned", "Planned"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    ON_HOLD = "on_hold", "On Hold"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    ARCHIVED = "archived", "Archived"


class ConstructionProjectVisibility(models.TextChoices):
    OWNER_ONLY = "owner_only", "Owner Only"
    STAKEHOLDERS = "stakeholders", "Stakeholders"
    ADMIN_ONLY = "admin_only", "Admin Only"


class ProjectStakeholderRole(models.TextChoices):
    OWNER = "owner", "Owner"
    INVESTOR = "investor", "Investor"
    PROJECT_MANAGER = "project_manager", "Project Manager"
    CONTRACTOR = "contractor", "Contractor"
    INSPECTOR = "inspector", "Inspector"
    VIEWER = "viewer", "Viewer"


class ProjectStakeholderStatus(models.TextChoices):
    INVITED = "invited", "Invited"
    ACTIVE = "active", "Active"
    DECLINED = "declined", "Declined"
    REVOKED = "revoked", "Revoked"
    EXPIRED = "expired", "Expired"


class ProjectAccessLevel(models.TextChoices):
    READ_ONLY = "read_only", "Read Only"
    COMMENTER = "commenter", "Commenter"
    OPERATOR = "operator", "Operator"
    MANAGER = "manager", "Manager"
    OWNER = "owner", "Owner"


class ConstructionMilestoneStatus(models.TextChoices):
    NOT_STARTED = "not_started", "Not Started"
    READY = "ready", "Ready"
    IN_PROGRESS = "in_progress", "In Progress"
    BLOCKED = "blocked", "Blocked"
    AWAITING_INSPECTION = "awaiting_inspection", "Awaiting Inspection"
    COMPLETED = "completed", "Completed"
    SKIPPED = "skipped", "Skipped"
    CANCELLED = "cancelled", "Cancelled"


class ConstructionProgressUpdateStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    REVISION_REQUESTED = "revision_requested", "Revision Requested"
    ARCHIVED = "archived", "Archived"


class ConstructionEvidenceType(models.TextChoices):
    PHOTO = "photo", "Photo"
    VIDEO = "video", "Video"
    DOCUMENT = "document", "Document"


class ConstructionEvidenceVisibility(models.TextChoices):
    PROJECT_STAKEHOLDERS = "project_stakeholders", "Project Stakeholders"
    OWNER_AND_ADMINS = "owner_and_admins", "Owner and Admins"
    ADMINS_ONLY = "admins_only", "Admins Only"


class ConstructionEvidenceStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"
