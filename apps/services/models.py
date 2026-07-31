from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from apps.common.models import BaseModel
from apps.services.choices import ProviderStatus, ProviderTradeStatus, ProviderType, SkillLevel


class TradeCategory(BaseModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=160, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=80, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    requires_certification = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["parent", "is_active", "display_order"]),
            models.Index(fields=["name"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["parent", "name"],
                condition=Q(deleted_at__isnull=True),
                name="unique_active_trade_category_name_per_parent",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self) -> str:
        base_slug = slugify(self.name)[:140] or "trade-category"
        candidate = base_slug
        counter = 2
        queryset = TradeCategory.all_objects.all()
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)
        while queryset.filter(slug=candidate).exists():
            suffix = f"-{counter}"
            candidate = f"{base_slug[: 160 - len(suffix)]}{suffix}"
            counter += 1
        return candidate


class ServiceProvider(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="service_provider_profile",
    )
    provider_type = models.CharField(
        max_length=20,
        choices=ProviderType.choices,
        default=ProviderType.INDIVIDUAL,
    )
    business_name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, unique=True)
    headline = models.CharField(max_length=180, blank=True)
    biography = models.TextField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    country = models.CharField(max_length=100, default="Nigeria")
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=120)
    lga = models.CharField(max_length=120, blank=True)
    neighborhood = models.CharField(max_length=160, blank=True)
    private_address = models.TextField(blank=True)
    display_location = models.CharField(max_length=220, blank=True)
    verification_snapshot = models.JSONField(default=dict, blank=True)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    completed_jobs_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=32,
        choices=ProviderStatus.choices,
        default=ProviderStatus.DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["business_name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["provider_type", "status"]),
            models.Index(fields=["state", "city", "status"]),
            models.Index(fields=["lga", "status"]),
            models.Index(fields=["average_rating"]),
            models.Index(fields=["completed_jobs_count"]),
        ]

    def __str__(self) -> str:
        return self.business_name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self) -> str:
        base_slug = slugify(self.business_name)[:190] or "service-provider"
        candidate = base_slug
        counter = 2
        queryset = ServiceProvider.all_objects.all()
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)
        while queryset.filter(slug=candidate).exists():
            suffix = f"-{counter}"
            candidate = f"{base_slug[: 220 - len(suffix)]}{suffix}"
            counter += 1
        return candidate

    @property
    def public_display_location(self) -> str:
        if self.display_location:
            return self.display_location
        parts = [self.neighborhood, self.city, self.state]
        return ", ".join(part for part in parts if part)


class ProviderTrade(BaseModel):
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name="trades",
    )
    category = models.ForeignKey(
        TradeCategory,
        on_delete=models.PROTECT,
        related_name="provider_trades",
    )
    is_primary = models.BooleanField(default=False)
    years_experience = models.PositiveSmallIntegerField(null=True, blank=True)
    skill_level = models.CharField(
        max_length=20,
        choices=SkillLevel.choices,
        default=SkillLevel.INTERMEDIATE,
    )
    status = models.CharField(
        max_length=20,
        choices=ProviderTradeStatus.choices,
        default=ProviderTradeStatus.ACTIVE,
    )

    class Meta:
        ordering = ["-is_primary", "category__name"]
        indexes = [
            models.Index(fields=["provider", "status"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["is_primary"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "category"],
                condition=Q(deleted_at__isnull=True),
                name="unique_active_provider_trade_category",
            ),
            models.UniqueConstraint(
                fields=["provider"],
                condition=Q(is_primary=True, deleted_at__isnull=True),
                name="unique_primary_trade_per_provider",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider.business_name} - {self.category.name}"


class ServiceArea(BaseModel):
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name="service_areas",
    )
    country = models.CharField(max_length=100, default="Nigeria")
    state = models.CharField(max_length=100)
    city = models.CharField(max_length=120)
    lga = models.CharField(max_length=120, blank=True)
    neighborhood = models.CharField(max_length=160, blank=True)
    service_radius_km = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["state", "city", "lga", "neighborhood"]
        indexes = [
            models.Index(fields=["provider"]),
            models.Index(fields=["state", "city"]),
            models.Index(fields=["lga"]),
            models.Index(fields=["neighborhood"]),
        ]

    def __str__(self) -> str:
        parts = [self.neighborhood, self.lga, self.city, self.state]
        return ", ".join(part for part in parts if part)
