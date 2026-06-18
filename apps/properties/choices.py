from django.db import models


class ListingType(models.TextChoices):
    SALE = "sale", "Sale"
    RENT = "rent", "Rent"


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
