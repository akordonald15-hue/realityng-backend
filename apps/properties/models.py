from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.common.models import BaseModel, UUIDPrimaryKeyMixin
from apps.properties.choices import (
    ContactPreference,
    GeocodingStatus,
    InquiryStatus,
    InquiryType,
    LeadActivityType,
    LeadPipelineStage,
    LeadPriority,
    ListingType,
    LocationPrecision,
    PropertyStatus,
    PropertyType,
    RentalApplicationStatus,
    ViewingStatus,
    ViewingType,
)


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
    lga = models.CharField(max_length=120, blank=True)
    neighborhood = models.CharField(max_length=160, blank=True)
    landmark = models.CharField(max_length=160, blank=True)
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_precision = models.CharField(
        max_length=20,
        choices=LocationPrecision.choices,
        default=LocationPrecision.NEIGHBORHOOD,
    )
    show_exact_location = models.BooleanField(default=False)
    geocoding_status = models.CharField(
        max_length=20,
        choices=GeocodingStatus.choices,
        default=GeocodingStatus.NOT_GEOCODED,
    )
    display_location = models.CharField(max_length=220, blank=True)
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
            models.Index(fields=["state", "city", "status"]),
            models.Index(fields=["lga", "status"]),
            models.Index(fields=["neighborhood", "status"]),
            models.Index(fields=["latitude", "longitude"]),
            models.Index(fields=["location_precision", "status"]),
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

    def public_display_location(self) -> str:
        if self.display_location:
            return self.display_location
        parts = [self.neighborhood, self.city, self.state]
        return ", ".join(part for part in parts if part)

    @property
    def approximate_location(self) -> bool:
        return not (self.location_precision == LocationPrecision.EXACT and self.show_exact_location)

    def public_coordinates(self) -> tuple[Decimal | None, Decimal | None]:
        if self.latitude is None or self.longitude is None:
            return None, None
        if self.location_precision == LocationPrecision.HIDDEN:
            return None, None
        if self.location_precision == LocationPrecision.EXACT and self.show_exact_location:
            return self.latitude, self.longitude
        decimal_places = 3 if self.location_precision == LocationPrecision.NEIGHBORHOOD else 2
        return round(self.latitude, decimal_places), round(self.longitude, decimal_places)


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


class Inquiry(BaseModel):
    VALID_STATUS_TRANSITIONS = {
        InquiryStatus.NEW: {InquiryStatus.CONTACTED, InquiryStatus.CLOSED},
        InquiryStatus.CONTACTED: {InquiryStatus.VIEWING_SCHEDULED, InquiryStatus.CLOSED},
        InquiryStatus.VIEWING_SCHEDULED: {InquiryStatus.NEGOTIATING, InquiryStatus.CLOSED},
        InquiryStatus.NEGOTIATING: {InquiryStatus.CONVERTED, InquiryStatus.CLOSED},
        InquiryStatus.CONVERTED: set(),
        InquiryStatus.CLOSED: set(),
    }

    VALID_PIPELINE_TRANSITIONS = {
        LeadPipelineStage.NEW: {
            LeadPipelineStage.CONTACTED,
            LeadPipelineStage.QUALIFIED,
            LeadPipelineStage.CLOSED_LOST,
        },
        LeadPipelineStage.CONTACTED: {
            LeadPipelineStage.QUALIFIED,
            LeadPipelineStage.CLOSED_LOST,
        },
        LeadPipelineStage.QUALIFIED: {
            LeadPipelineStage.VIEWING_SCHEDULED,
            LeadPipelineStage.CLOSED_LOST,
        },
        LeadPipelineStage.VIEWING_SCHEDULED: {
            LeadPipelineStage.APPLICATION_STARTED,
            LeadPipelineStage.NEGOTIATING,
            LeadPipelineStage.CLOSED_LOST,
        },
        LeadPipelineStage.APPLICATION_STARTED: {
            LeadPipelineStage.APPLICATION_SUBMITTED,
            LeadPipelineStage.CLOSED_LOST,
        },
        LeadPipelineStage.APPLICATION_SUBMITTED: {
            LeadPipelineStage.NEGOTIATING,
            LeadPipelineStage.CLOSED_LOST,
        },
        LeadPipelineStage.NEGOTIATING: {
            LeadPipelineStage.CONVERTED,
            LeadPipelineStage.CLOSED_LOST,
        },
        LeadPipelineStage.CONVERTED: set(),
        LeadPipelineStage.CLOSED_LOST: set(),
    }

    property = models.ForeignKey(
        Property,
        on_delete=models.PROTECT,
        related_name="inquiries",
    )
    interested_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="property_inquiries",
    )
    property_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_property_inquiries",
    )
    inquiry_type = models.CharField(max_length=32, choices=InquiryType.choices)
    message = models.TextField(blank=True)
    contact_preference = models.CharField(
        max_length=20,
        choices=ContactPreference.choices,
        default=ContactPreference.EMAIL,
    )
    status = models.CharField(
        max_length=32,
        choices=InquiryStatus.choices,
        default=InquiryStatus.NEW,
    )
    internal_notes = models.TextField(blank=True)

    pipeline_stage = models.CharField(
        max_length=32,
        choices=LeadPipelineStage.choices,
        default=LeadPipelineStage.NEW,
    )
    priority = models.CharField(
        max_length=16,
        choices=LeadPriority.choices,
        default=LeadPriority.MEDIUM,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_leads",
    )
    source = models.CharField(max_length=64, blank=True)
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    next_follow_up_at = models.DateTimeField(null=True, blank=True)
    follow_up_count = models.PositiveIntegerField(default=0)
    closed_reason = models.CharField(max_length=255, blank=True)
    conversion_value = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    converted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["interested_user", "status", "created_at"]),
            models.Index(fields=["property_owner", "status", "created_at"]),
            models.Index(fields=["property", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["inquiry_type"]),
            models.Index(fields=["pipeline_stage", "created_at"]),
            models.Index(fields=["assigned_to", "pipeline_stage"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["next_follow_up_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_inquiry_type_display()} inquiry for {self.property.title}"

    def can_transition_to(self, next_status: str) -> bool:
        return next_status in self.VALID_STATUS_TRANSITIONS.get(self.status, set())

    def transition_to(self, next_status: str) -> None:
        if next_status == self.status:
            return
        if not self.can_transition_to(next_status):
            raise ValueError(f"Inquiry cannot move from {self.status} to {next_status}.")
        self.status = next_status
        self.save(update_fields=["status", "updated_at"])

    def can_transition_pipeline_to(self, next_stage: str) -> bool:
        return next_stage in self.VALID_PIPELINE_TRANSITIONS.get(self.pipeline_stage, set())

    def transition_pipeline_to(self, next_stage: str) -> None:
        if next_stage == self.pipeline_stage:
            return
        if not self.can_transition_pipeline_to(next_stage):
            raise ValueError(
                f"Lead cannot move from {self.pipeline_stage} to {next_stage}."
            )
        update_fields = ["pipeline_stage", "updated_at"]
        self.pipeline_stage = next_stage
        if next_stage == LeadPipelineStage.CONVERTED:
            self.converted_at = timezone.now()
            update_fields.append("converted_at")
        self.save(update_fields=update_fields)


class LeadActivity(BaseModel):
    inquiry = models.ForeignKey(
        Inquiry,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="lead_activities",
    )
    activity_type = models.CharField(
        max_length=32,
        choices=LeadActivityType.choices,
    )
    note = models.TextField(blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["inquiry", "created_at"]),
            models.Index(fields=["inquiry", "activity_type"]),
            models.Index(fields=["scheduled_for"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_activity_type_display()} on inquiry {self.inquiry_id}"


class Viewing(BaseModel):
    VALID_STATUS_TRANSITIONS = {
        ViewingStatus.REQUESTED: {
            ViewingStatus.CONFIRMED,
            ViewingStatus.RESCHEDULED,
            ViewingStatus.CANCELLED,
        },
        ViewingStatus.RESCHEDULED: {
            ViewingStatus.CONFIRMED,
            ViewingStatus.CANCELLED,
        },
        ViewingStatus.CONFIRMED: {
            ViewingStatus.COMPLETED,
            ViewingStatus.CANCELLED,
        },
        ViewingStatus.COMPLETED: set(),
        ViewingStatus.CANCELLED: set(),
    }

    inquiry = models.ForeignKey(
        Inquiry,
        on_delete=models.PROTECT,
        related_name="viewings",
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.PROTECT,
        related_name="viewings",
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="viewing_requests",
    )
    property_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_viewing_requests",
    )
    viewing_type = models.CharField(max_length=20, choices=ViewingType.choices)
    preferred_date = models.DateField()
    preferred_time = models.TimeField()
    confirmed_datetime = models.DateTimeField(null=True, blank=True)
    meeting_location = models.CharField(max_length=240, blank=True)
    meeting_link = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=32,
        choices=ViewingStatus.choices,
        default=ViewingStatus.REQUESTED,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["requester", "status", "created_at"]),
            models.Index(fields=["property_owner", "status", "created_at"]),
            models.Index(fields=["property", "status"]),
            models.Index(fields=["inquiry", "status"]),
            models.Index(fields=["preferred_date", "preferred_time"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_viewing_type_display()} viewing for {self.property.title}"

    def can_transition_to(self, next_status: str) -> bool:
        return next_status in self.VALID_STATUS_TRANSITIONS.get(self.status, set())

    def transition_to(self, next_status: str) -> None:
        if next_status == self.status:
            return
        if not self.can_transition_to(next_status):
            raise ValueError(f"Viewing cannot move from {self.status} to {next_status}.")
        self.status = next_status
        self.save(update_fields=["status", "updated_at"])


class RentalApplication(BaseModel):
    VALID_STATUS_TRANSITIONS = {
        RentalApplicationStatus.SUBMITTED: {
            RentalApplicationStatus.UNDER_REVIEW,
            RentalApplicationStatus.WITHDRAWN,
        },
        RentalApplicationStatus.UNDER_REVIEW: {
            RentalApplicationStatus.APPROVED,
            RentalApplicationStatus.REJECTED,
            RentalApplicationStatus.WITHDRAWN,
        },
        RentalApplicationStatus.APPROVED: set(),
        RentalApplicationStatus.REJECTED: set(),
        RentalApplicationStatus.WITHDRAWN: set(),
    }

    property = models.ForeignKey(
        Property,
        on_delete=models.PROTECT,
        related_name="rental_applications",
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rental_applications",
    )
    property_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_rental_applications",
    )
    inquiry = models.ForeignKey(
        Inquiry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rental_applications",
    )
    viewing = models.ForeignKey(
        Viewing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rental_applications",
    )
    full_name = models.CharField(max_length=160)
    email = models.EmailField()
    phone = models.CharField(max_length=40)
    employment_status = models.CharField(max_length=80)
    employer_name = models.CharField(max_length=160, blank=True)
    monthly_income = models.DecimalField(max_digits=14, decimal_places=2)
    move_in_date = models.DateField()
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=32,
        choices=RentalApplicationStatus.choices,
        default=RentalApplicationStatus.SUBMITTED,
    )
    owner_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["applicant", "status", "created_at"]),
            models.Index(fields=["property_owner", "status", "created_at"]),
            models.Index(fields=["property", "status"]),
            models.Index(fields=["inquiry", "status"]),
            models.Index(fields=["viewing", "status"]),
            models.Index(fields=["move_in_date"]),
        ]

    def __str__(self) -> str:
        return f"Application from {self.full_name} for {self.property.title}"

    def can_transition_to(self, next_status: str) -> bool:
        return next_status in self.VALID_STATUS_TRANSITIONS.get(self.status, set())

    def transition_to(self, next_status: str) -> None:
        if next_status == self.status:
            return
        if not self.can_transition_to(next_status):
            raise ValueError(f"Application cannot move from {self.status} to {next_status}.")
        self.status = next_status
        self.save(update_fields=["status", "updated_at"])
