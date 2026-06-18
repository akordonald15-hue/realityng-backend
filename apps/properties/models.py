from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import BaseModel
from apps.properties.choices import ListingType, PropertyStatus, PropertyType


class Property(BaseModel):
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField()
    property_type = models.CharField(max_length=40, choices=PropertyType.choices)
    listing_type = models.CharField(max_length=20, choices=ListingType.choices)
    price = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=120)
    address = models.TextField()
    bedrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    bathrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    parking_spaces = models.PositiveSmallIntegerField(null=True, blank=True)
    land_size = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    floor_area = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=PropertyStatus.choices,
        default=PropertyStatus.DRAFT,
    )
    featured = models.BooleanField(default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="properties",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["city", "status"]),
            models.Index(fields=["property_type", "listing_type", "status"]),
            models.Index(fields=["price"]),
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self) -> str:
        base_slug = slugify(self.title)[:190] or "property"
        candidate = base_slug
        counter = 2
        queryset = Property.all_objects.all()
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        while queryset.filter(slug=candidate).exists():
            suffix = f"-{counter}"
            candidate = f"{base_slug[: 220 - len(suffix)]}{suffix}"
            counter += 1
        return candidate

    def submit_for_review(self) -> None:
        self.status = PropertyStatus.PENDING_REVIEW
        self.save(update_fields=["status", "updated_at"])

    def approve(self) -> None:
        self.status = PropertyStatus.APPROVED
        self.save(update_fields=["status", "updated_at"])

    def reject(self) -> None:
        self.status = PropertyStatus.REJECTED
        self.save(update_fields=["status", "updated_at"])

    @property
    def is_land(self) -> bool:
        return self.property_type == PropertyType.LAND

    @property
    def price_as_decimal(self) -> Decimal:
        return Decimal(self.price)
