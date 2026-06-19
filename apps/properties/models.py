from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils.text import slugify

from apps.common.models import BaseModel, UUIDPrimaryKeyMixin
from apps.properties.choices import ListingType, PropertyStatus, PropertyType


def property_image_upload_to(instance: PropertyImage, filename: str) -> str:
    return f"properties/{instance.property_id}/images/{filename}"


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


class PropertyImage(UUIDPrimaryKeyMixin):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to=property_image_upload_to)
    caption = models.CharField(max_length=180, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["display_order", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["property"],
                condition=models.Q(is_cover=True),
                name="unique_cover_image_per_property",
            ),
        ]
        indexes = [
            models.Index(fields=["property", "display_order"]),
            models.Index(fields=["property", "is_cover"]),
        ]

    def __str__(self) -> str:
        return f"{self.property.title} image"

    def save(self, *args, **kwargs) -> None:
        with transaction.atomic():
            if self.is_cover:
                PropertyImage.objects.filter(property_id=self.property_id).exclude(pk=self.pk).update(
                    is_cover=False
                )
            super().save(*args, **kwargs)

    def set_as_cover(self) -> None:
        self.is_cover = True
        self.save(update_fields=["is_cover"])


class Favorite(UUIDPrimaryKeyMixin):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "property"],
                name="unique_favorite_per_user_property",
            ),
        ]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["property"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} saved {self.property_id}"
