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


class LocationPrecision(models.TextChoices):
    EXACT = "exact", "Exact"
    NEIGHBORHOOD = "neighborhood", "Neighborhood"
    CITY = "city", "City"
    HIDDEN = "hidden", "Hidden"


class GeocodingStatus(models.TextChoices):
    NOT_GEOCODED = "not_geocoded", "Not Geocoded"
    PENDING = "pending", "Pending"
    GEOCODED = "geocoded", "Geocoded"
    FAILED = "failed", "Failed"
    MANUAL = "manual", "Manual"


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


class RentalApplicationStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"


class PropertyAssignmentType(models.TextChoices):
    AGENT = "agent", "Agent"
    PROPERTY_MANAGER = "property_manager", "Property Manager"
    CARETAKER = "caretaker", "Caretaker"
    PROJECT_MANAGER = "project_manager", "Project Manager"
    AUTHORIZED_REPRESENTATIVE = "authorized_representative", "Authorized Representative"


class PropertyAssignmentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    REVOKED = "revoked", "Revoked"
    EXPIRED = "expired", "Expired"
    DECLINED = "declined", "Declined"


class PropertyAssignmentCapability(models.TextChoices):
    MANAGE_LISTING = "manage_listing", "Manage Listing"
    MANAGE_WALKTHROUGHS = "manage_walkthroughs", "Manage Walkthroughs"
    MANAGE_VIEWINGS = "manage_viewings", "Manage Viewings"
    MANAGE_INSPECTIONS = "manage_inspections", "Manage Inspections"
    MANAGE_CONSTRUCTION = "manage_construction", "Manage Construction"
    VIEW_PRIVATE_PROJECT_DATA = "view_private_project_data", "View Private Project Data"
