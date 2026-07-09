from django.db import models


class ListingType(models.TextChoices):
    SALE = "sale", "Sale"
    RENT = "rent", "Rent"
    APARTMENT_SHARE = "apartment_share", "Apartment Share"


class PropertyStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_REVIEW = "pending_review", "Pending Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    ARCHIVED = "archived", "Archived"


class PropertyType(models.TextChoices):
    APARTMENT = "apartment", "Apartment"
    HOUSE = "house", "House"
    LAND = "land", "Land"
    COMMERCIAL = "commercial", "Commercial"
    OFFICE = "office", "Office"
    SHOP = "shop", "Shop"
    WAREHOUSE = "warehouse", "Warehouse"
    MIXED_USE = "mixed_use", "Mixed Use"


class InquiryType(models.TextChoices):
    RENT = "rent", "Rent"
    PURCHASE = "purchase", "Purchase"
    APARTMENT_SHARE = "apartment_share", "Apartment Share"


class InquiryStatus(models.TextChoices):
    NEW = "new", "New"
    CONTACTED = "contacted", "Contacted"
    VIEWING_SCHEDULED = "viewing_scheduled", "Viewing Scheduled"
    NEGOTIATING = "negotiating", "Negotiating"
    CONVERTED = "converted", "Converted"
    CLOSED = "closed", "Closed"


class ContactPreference(models.TextChoices):
    EMAIL = "email", "Email"
    PHONE = "phone", "Phone"
    WHATSAPP = "whatsapp", "WhatsApp"


class ViewingType(models.TextChoices):
    PHYSICAL = "physical", "Physical"
    VIRTUAL = "virtual", "Virtual"


class ViewingStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    RESCHEDULED = "rescheduled", "Rescheduled"
    CONFIRMED = "confirmed", "Confirmed"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
