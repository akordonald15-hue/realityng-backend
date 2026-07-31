from django.db import models


class ProviderType(models.TextChoices):
    INDIVIDUAL = "individual", "Individual"
    COMPANY = "company", "Company"


class ProviderStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_REVIEW = "pending_review", "Pending Review"
    ACTIVE = "active", "Active"
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
