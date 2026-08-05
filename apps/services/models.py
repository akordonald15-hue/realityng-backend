from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from apps.common.models import BaseModel
from apps.services.choices import (
    PortfolioImageStatus,
    PreferredContactMethod,
    ProviderAppealStatus,
    ProviderAppealType,
    ProviderStatus,
    ProviderSuspensionType,
    ProviderTradeStatus,
    ProviderType,
    QuoteRequestStatus,
    ServiceBookingStatus,
    ServiceComplaintCategory,
    ServiceComplaintStatus,
    ServiceComplaintType,
    ServiceReviewFlagReason,
    ServiceReviewStatus,
    SkillLevel,
)


def portfolio_image_upload_to(instance: PortfolioImage, filename: str) -> str:
    return f"services/{instance.provider_id}/portfolio/{filename}"


def complaint_evidence_upload_to(instance: ServiceComplaintEvidence, filename: str) -> str:
    return f"services/complaints/{instance.complaint_id}/evidence/{filename}"


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
    average_quality_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    average_punctuality_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    average_communication_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    average_value_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    published_review_count = models.PositiveIntegerField(default=0)
    recommendation_percentage = models.PositiveSmallIntegerField(default=0)
    completed_jobs_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=32,
        choices=ProviderStatus.choices,
        default=ProviderStatus.DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_service_providers",
    )
    review_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    more_info_message = models.TextField(blank=True)
    suspended_reason = models.TextField(blank=True)
    warning_count = models.PositiveSmallIntegerField(default=0)
    last_warning_reason = models.TextField(blank=True)
    suspension_type = models.CharField(
        max_length=20,
        choices=ProviderSuspensionType.choices,
        blank=True,
    )
    suspension_expires_at = models.DateTimeField(null=True, blank=True)
    appeal_status = models.CharField(
        max_length=20,
        choices=ProviderAppealStatus.choices,
        blank=True,
    )

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
            models.Index(fields=["suspension_type", "suspension_expires_at"]),
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

    def submit_for_review(self) -> None:
        self.status = ProviderStatus.PENDING_REVIEW
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "submitted_at", "updated_at"])

    def approve(self, *, reviewer) -> None:
        self.status = ProviderStatus.ACTIVE
        self.published_at = timezone.now()
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.rejection_reason = ""
        self.more_info_message = ""
        self.suspended_reason = ""
        self.save(
            update_fields=[
                "status",
                "published_at",
                "reviewed_at",
                "reviewed_by",
                "rejection_reason",
                "more_info_message",
                "suspended_reason",
                "updated_at",
            ]
        )

    def reject(self, *, reviewer, reason: str) -> None:
        self.status = ProviderStatus.REJECTED
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.rejection_reason = reason
        self.save(
            update_fields=[
                "status",
                "reviewed_at",
                "reviewed_by",
                "rejection_reason",
                "updated_at",
            ]
        )

    def request_more_information(self, *, reviewer, message: str) -> None:
        self.status = ProviderStatus.NEEDS_MORE_INFORMATION
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.more_info_message = message
        self.save(
            update_fields=[
                "status",
                "reviewed_at",
                "reviewed_by",
                "more_info_message",
                "updated_at",
            ]
        )

    def warn(self, *, reviewer, reason: str) -> None:
        self.warning_count += 1
        self.last_warning_reason = reason
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.save(
            update_fields=[
                "warning_count",
                "last_warning_reason",
                "reviewed_at",
                "reviewed_by",
                "updated_at",
            ]
        )

    def suspend(
        self,
        *,
        reviewer,
        reason: str,
        suspension_type: str = ProviderSuspensionType.TEMPORARY,
        expires_at=None,
    ) -> None:
        self.status = ProviderStatus.SUSPENDED
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.suspended_reason = reason
        self.suspension_type = suspension_type
        self.suspension_expires_at = expires_at
        self.save(
            update_fields=[
                "status",
                "reviewed_at",
                "reviewed_by",
                "suspended_reason",
                "suspension_type",
                "suspension_expires_at",
                "updated_at",
            ]
        )

    def reactivate(self, *, reviewer) -> None:
        self.status = ProviderStatus.ACTIVE
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.suspended_reason = ""
        self.suspension_type = ""
        self.suspension_expires_at = None
        self.appeal_status = ""
        if not self.published_at:
            self.published_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "reviewed_at",
                "reviewed_by",
                "suspended_reason",
                "suspension_type",
                "suspension_expires_at",
                "appeal_status",
                "published_at",
                "updated_at",
            ]
        )

    def deactivate(self) -> None:
        self.status = ProviderStatus.INACTIVE
        self.save(update_fields=["status", "updated_at"])


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

    def save(self, *args, **kwargs) -> None:
        with transaction.atomic():
            if self.is_primary:
                ProviderTrade.objects.filter(provider_id=self.provider_id).exclude(pk=self.pk).update(
                    is_primary=False
                )
            super().save(*args, **kwargs)


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
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["state", "city", "lga", "neighborhood"]
        indexes = [
            models.Index(fields=["provider"]),
            models.Index(fields=["state", "city"]),
            models.Index(fields=["lga"]),
            models.Index(fields=["neighborhood"]),
            models.Index(fields=["provider", "is_primary"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider"],
                condition=Q(is_primary=True, deleted_at__isnull=True),
                name="unique_primary_service_area_per_provider",
            ),
        ]

    def __str__(self) -> str:
        parts = [self.neighborhood, self.lga, self.city, self.state]
        return ", ".join(part for part in parts if part)

    def save(self, *args, **kwargs) -> None:
        with transaction.atomic():
            if self.is_primary:
                ServiceArea.objects.filter(provider_id=self.provider_id).exclude(pk=self.pk).update(
                    is_primary=False
                )
            super().save(*args, **kwargs)


class PortfolioImage(BaseModel):
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.CASCADE,
        related_name="portfolio_images",
    )
    image = models.ImageField(upload_to=portfolio_image_upload_to)
    caption = models.CharField(max_length=180, blank=True)
    category = models.ForeignKey(
        TradeCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="portfolio_images",
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=PortfolioImageStatus.choices,
        default=PortfolioImageStatus.ACTIVE,
    )

    class Meta:
        ordering = ["display_order", "created_at"]
        indexes = [
            models.Index(fields=["provider", "display_order"]),
            models.Index(fields=["provider", "is_cover"]),
            models.Index(fields=["provider", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider"],
                condition=Q(is_cover=True, deleted_at__isnull=True),
                name="unique_cover_portfolio_image_per_provider",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider.business_name} portfolio image"

    def save(self, *args, **kwargs) -> None:
        with transaction.atomic():
            if self.is_cover:
                PortfolioImage.objects.filter(provider_id=self.provider_id).exclude(
                    pk=self.pk
                ).update(is_cover=False)
            super().save(*args, **kwargs)

    def set_as_cover(self) -> None:
        self.is_cover = True
        self.save(update_fields=["is_cover", "updated_at"])


class QuoteRequest(BaseModel):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_quote_requests",
    )
    customer_name = models.CharField(max_length=160)
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.PROTECT,
        related_name="quote_requests",
    )
    service_category = models.ForeignKey(
        TradeCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="quote_requests",
    )
    project_title = models.CharField(max_length=180)
    project_description = models.TextField()
    budget_range = models.CharField(max_length=120, blank=True)
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=PreferredContactMethod.choices,
        default=PreferredContactMethod.PHONE,
    )
    phone = models.CharField(max_length=40)
    email = models.EmailField()
    property_address = models.TextField(blank=True)
    state = models.CharField(max_length=80)
    lga = models.CharField(max_length=120, blank=True)
    preferred_start_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=QuoteRequestStatus.choices,
        default=QuoteRequestStatus.SUBMITTED,
        db_index=True,
    )
    viewed_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "status", "created_at"]),
            models.Index(fields=["customer", "created_at"]),
            models.Index(fields=["state", "lga"]),
        ]

    def __str__(self) -> str:
        return f"{self.project_title} for {self.provider.business_name}"

    def mark_viewed(self) -> None:
        if self.status == QuoteRequestStatus.SUBMITTED:
            self.status = QuoteRequestStatus.VIEWED
            self.viewed_at = timezone.now()
            self.save(update_fields=["status", "viewed_at", "updated_at"])

    def mark_responded(self) -> None:
        if self.status in [QuoteRequestStatus.SUBMITTED, QuoteRequestStatus.VIEWED]:
            self.status = QuoteRequestStatus.RESPONDED
            self.responded_at = timezone.now()
            if not self.viewed_at:
                self.viewed_at = self.responded_at
            self.save(update_fields=["status", "responded_at", "viewed_at", "updated_at"])

    def close(self) -> None:
        if self.status not in [QuoteRequestStatus.CLOSED, QuoteRequestStatus.CANCELLED]:
            self.status = QuoteRequestStatus.CLOSED
            self.closed_at = timezone.now()
            self.save(update_fields=["status", "closed_at", "updated_at"])

    def cancel(self) -> None:
        if self.status not in [QuoteRequestStatus.CLOSED, QuoteRequestStatus.CANCELLED]:
            self.status = QuoteRequestStatus.CANCELLED
            self.closed_at = timezone.now()
            self.save(update_fields=["status", "closed_at", "updated_at"])


class ServiceBooking(BaseModel):
    quote_request = models.OneToOneField(
        QuoteRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="service_booking",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="service_bookings",
    )
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.PROTECT,
        related_name="service_bookings",
    )
    service_category = models.ForeignKey(
        TradeCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="service_bookings",
    )
    title = models.CharField(max_length=180)
    service_summary = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ServiceBookingStatus.choices,
        default=ServiceBookingStatus.PENDING,
        db_index=True,
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "status", "created_at"]),
            models.Index(fields=["customer", "status", "created_at"]),
            models.Index(fields=["completed_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(status=ServiceBookingStatus.COMPLETED, completed_at__isnull=False)
                    | ~Q(status=ServiceBookingStatus.COMPLETED)
                ),
                name="completed_service_booking_has_completed_at",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} with {self.provider.business_name}"

    @property
    def is_review_eligible(self) -> bool:
        return self.status == ServiceBookingStatus.COMPLETED and bool(self.completed_at)

    def clean(self) -> None:
        if self.provider_id and self.customer_id == self.provider.user_id:
            raise ValidationError({"customer": "Providers cannot book their own services."})
        if self.status == ServiceBookingStatus.COMPLETED and not self.completed_at:
            raise ValidationError({"completed_at": "Completed bookings require a completion time."})
        if self.service_category_id and self.provider_id:
            has_category = self.provider.trades.filter(
                category_id=self.service_category_id,
                status=ProviderTradeStatus.ACTIVE,
            ).exists()
            if not has_category:
                raise ValidationError(
                    {"service_category": "This provider does not offer that active trade."}
                )

    def confirm(self) -> None:
        if self.status == ServiceBookingStatus.PENDING:
            self.status = ServiceBookingStatus.CONFIRMED
            self.confirmed_at = timezone.now()
            self.save(update_fields=["status", "confirmed_at", "updated_at"])

    def complete(self) -> None:
        if self.status not in [ServiceBookingStatus.COMPLETED, ServiceBookingStatus.CANCELLED]:
            self.status = ServiceBookingStatus.COMPLETED
            self.completed_at = timezone.now()
            self.save(update_fields=["status", "completed_at", "updated_at"])

    def cancel(self) -> None:
        if self.status != ServiceBookingStatus.COMPLETED:
            self.status = ServiceBookingStatus.CANCELLED
            self.cancelled_at = timezone.now()
            self.save(update_fields=["status", "cancelled_at", "updated_at"])


class ServiceReview(BaseModel):
    booking = models.OneToOneField(
        ServiceBooking,
        on_delete=models.PROTECT,
        related_name="review",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="service_reviews",
    )
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.PROTECT,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=160)
    comment = models.TextField()
    would_recommend = models.BooleanField(default=True)
    quality_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    punctuality_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    communication_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    value_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ServiceReviewStatus.choices,
        default=ServiceReviewStatus.PENDING,
        db_index=True,
    )
    provider_response = models.TextField(blank=True)
    provider_responded_at = models.DateTimeField(null=True, blank=True)
    moderation_reason = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    creation_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    risk_flags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "status", "created_at"]),
            models.Index(fields=["customer", "created_at"]),
            models.Index(fields=["rating", "created_at"]),
            models.Index(fields=["published_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(rating__gte=1, rating__lte=5),
                name="service_review_rating_between_1_and_5",
            ),
            models.CheckConstraint(
                condition=(
                    Q(quality_rating__isnull=True)
                    | Q(quality_rating__gte=1, quality_rating__lte=5)
                ),
                name="service_review_quality_rating_between_1_and_5",
            ),
            models.CheckConstraint(
                condition=(
                    Q(punctuality_rating__isnull=True)
                    | Q(punctuality_rating__gte=1, punctuality_rating__lte=5)
                ),
                name="service_review_punctuality_rating_between_1_and_5",
            ),
            models.CheckConstraint(
                condition=(
                    Q(communication_rating__isnull=True)
                    | Q(communication_rating__gte=1, communication_rating__lte=5)
                ),
                name="service_review_communication_rating_between_1_and_5",
            ),
            models.CheckConstraint(
                condition=(
                    Q(value_rating__isnull=True)
                    | Q(value_rating__gte=1, value_rating__lte=5)
                ),
                name="service_review_value_rating_between_1_and_5",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.rating}/5 review for {self.provider.business_name}"

    def clean(self) -> None:
        if self.booking_id:
            if self.booking.customer_id != self.customer_id:
                raise ValidationError({"booking": "Only the booking customer can review."})
            if self.booking.provider_id != self.provider_id:
                raise ValidationError({"provider": "Review provider must match the booking."})
            if not self.booking.is_review_eligible:
                raise ValidationError({"booking": "Only completed bookings can be reviewed."})
        if self.provider_id and self.customer_id == self.provider.user_id:
            raise ValidationError({"customer": "Providers cannot review themselves."})

    def publish(self) -> None:
        if self.status != ServiceReviewStatus.PUBLISHED:
            self.status = ServiceReviewStatus.PUBLISHED
            self.published_at = self.published_at or timezone.now()
            self.save(update_fields=["status", "published_at", "updated_at"])

    def hide(self, reason: str) -> None:
        self.status = ServiceReviewStatus.HIDDEN
        self.moderation_reason = reason
        self.save(update_fields=["status", "moderation_reason", "updated_at"])

    def restore(self) -> None:
        self.status = ServiceReviewStatus.PUBLISHED
        self.published_at = self.published_at or timezone.now()
        self.save(update_fields=["status", "published_at", "updated_at"])

    def remove(self, reason: str) -> None:
        self.status = ServiceReviewStatus.REMOVED
        self.moderation_reason = reason
        self.save(update_fields=["status", "moderation_reason", "updated_at"])

    def mark_disputed(self, reason: str) -> None:
        self.status = ServiceReviewStatus.DISPUTED
        self.moderation_reason = reason
        self.save(update_fields=["status", "moderation_reason", "updated_at"])

    def respond(self, response: str) -> None:
        self.provider_response = response
        self.provider_responded_at = timezone.now()
        self.save(update_fields=["provider_response", "provider_responded_at", "updated_at"])


class ServiceReviewFlag(BaseModel):
    review = models.ForeignKey(
        ServiceReview,
        on_delete=models.PROTECT,
        related_name="flags",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="service_review_flags",
    )
    reason = models.CharField(
        max_length=40,
        choices=ServiceReviewFlagReason.choices,
    )
    details = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["review", "reason", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["review", "user"],
                condition=Q(deleted_at__isnull=True),
                name="unique_active_service_review_flag_per_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.reason} flag for {self.review_id}"


class ServiceComplaint(BaseModel):
    complainant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="service_complaints",
    )
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.PROTECT,
        related_name="complaints",
    )
    quote_request = models.ForeignKey(
        QuoteRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
    )
    review = models.ForeignKey(
        ServiceReview,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
    )
    booking = models.ForeignKey(
        ServiceBooking,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
    )
    complaint_type = models.CharField(max_length=20, choices=ServiceComplaintType.choices)
    category = models.CharField(
        max_length=40,
        choices=ServiceComplaintCategory.choices,
        default=ServiceComplaintCategory.OTHER,
    )
    subject = models.CharField(max_length=180)
    description = models.TextField()
    status = models.CharField(
        max_length=24,
        choices=ServiceComplaintStatus.choices,
        default=ServiceComplaintStatus.OPEN,
        db_index=True,
    )
    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_service_complaints",
    )
    resolution_notes = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["complainant", "created_at"]),
            models.Index(fields=["provider", "status", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["assigned_admin", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.subject} against {self.provider.business_name}"

    def clean(self) -> None:
        if self.provider_id and self.complainant_id == self.provider.user_id:
            if self.complaint_type != ServiceComplaintType.PROVIDER:
                raise ValidationError(
                    {"complaint_type": "Provider-owned complaints must use provider type."}
                )
        if self.quote_request_id and self.provider_id != self.quote_request.provider_id:
            raise ValidationError({"quote_request": "Quote request must belong to provider."})
        if self.review_id and self.provider_id != self.review.provider_id:
            raise ValidationError({"review": "Review must belong to provider."})
        if self.booking_id and self.provider_id != self.booking.provider_id:
            raise ValidationError({"booking": "Booking must belong to provider."})

    def set_status(self, *, new_status: str, actor=None, notes: str = "") -> None:
        self.status = new_status
        now = timezone.now()
        update_fields = ["status", "updated_at"]
        if notes:
            self.resolution_notes = notes
            update_fields.append("resolution_notes")
        if actor and getattr(actor, "is_authenticated", False):
            self.assigned_admin = actor
            update_fields.append("assigned_admin")
        if new_status == ServiceComplaintStatus.RESOLVED:
            self.resolved_at = now
            update_fields.append("resolved_at")
        elif new_status == ServiceComplaintStatus.REJECTED:
            self.rejected_at = now
            update_fields.append("rejected_at")
        elif new_status == ServiceComplaintStatus.ESCALATED:
            self.escalated_at = now
            update_fields.append("escalated_at")
        elif new_status == ServiceComplaintStatus.CLOSED:
            self.closed_at = now
            update_fields.append("closed_at")
        self.save(update_fields=update_fields)


class ServiceComplaintEvidence(BaseModel):
    complaint = models.ForeignKey(
        ServiceComplaint,
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    file = models.FileField(upload_to=complaint_evidence_upload_to)
    caption = models.CharField(max_length=180, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="service_complaint_evidence",
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["complaint", "created_at"]),
            models.Index(fields=["uploaded_by", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Evidence for {self.complaint_id}"


class ProviderAppeal(BaseModel):
    provider = models.ForeignKey(
        ServiceProvider,
        on_delete=models.PROTECT,
        related_name="appeals",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="service_provider_appeals",
    )
    appeal_type = models.CharField(max_length=20, choices=ProviderAppealType.choices)
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=ProviderAppealStatus.choices,
        default=ProviderAppealStatus.SUBMITTED,
        db_index=True,
    )
    admin_notes = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_service_provider_appeals",
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider", "status", "created_at"]),
            models.Index(fields=["submitted_by", "created_at"]),
            models.Index(fields=["appeal_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.appeal_type} appeal for {self.provider.business_name}"

    def clean(self) -> None:
        if self.provider_id and self.submitted_by_id != self.provider.user_id:
            raise ValidationError({"submitted_by": "Only the provider owner may appeal."})

    def decide(self, *, status_value: str, actor, notes: str = "") -> None:
        self.status = status_value
        self.decided_by = actor
        self.decided_at = timezone.now()
        if notes:
            self.admin_notes = notes
        self.save(
            update_fields=["status", "decided_by", "decided_at", "admin_notes", "updated_at"]
        )
        self.provider.appeal_status = status_value
        self.provider.save(update_fields=["appeal_status", "updated_at"])
