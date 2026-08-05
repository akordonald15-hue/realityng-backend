from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from apps.properties.serializers import build_media_url
from apps.services.choices import (
    PortfolioImageStatus,
    PreferredContactMethod,
    ProviderAppealStatus,
    ProviderAppealType,
    ProviderStatus,
    ProviderSuspensionType,
    ProviderTradeStatus,
    QuoteRequestStatus,
    ServiceComplaintCategory,
    ServiceComplaintStatus,
    ServiceComplaintType,
    ServiceReviewFlagReason,
    ServiceReviewStatus,
)
from apps.services.models import (
    PortfolioImage,
    ProviderAppeal,
    ProviderTrade,
    QuoteRequest,
    ServiceArea,
    ServiceBooking,
    ServiceComplaint,
    ServiceComplaintEvidence,
    ServiceProvider,
    ServiceReview,
    ServiceReviewFlag,
    TradeCategory,
)

EDITABLE_WITHOUT_REVIEW = {"headline", "biography", "phone", "email"}
MODERATION_SENSITIVE_FIELDS = {
    "provider_type",
    "business_name",
    "country",
    "state",
    "city",
    "lga",
    "neighborhood",
    "display_location",
    "private_address",
}


class TradeCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = TradeCategory
        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "description",
            "icon",
            "display_order",
            "requires_certification",
            "is_active",
            "children",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_children(self, obj):
        children = [
            child for child in getattr(obj, "prefetched_children", []) if child.is_active
        ]
        if not children and not hasattr(obj, "prefetched_children"):
            children = obj.children.filter(is_active=True)
        return TradeCategorySerializer(children, many=True, context=self.context).data


class ProviderTradeSerializer(serializers.ModelSerializer):
    category = TradeCategorySerializer(read_only=True)

    class Meta:
        model = ProviderTrade
        fields = [
            "id",
            "category",
            "is_primary",
            "years_experience",
            "skill_level",
        ]
        read_only_fields = fields


class ServiceAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceArea
        fields = [
            "id",
            "country",
            "state",
            "city",
            "lga",
            "neighborhood",
            "service_radius_km",
            "is_primary",
        ]
        read_only_fields = fields


class PortfolioImagePublicSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    category = TradeCategorySerializer(read_only=True)

    class Meta:
        model = PortfolioImage
        fields = [
            "id",
            "image_url",
            "caption",
            "category",
            "display_order",
            "is_cover",
            "created_at",
        ]
        read_only_fields = fields

    def get_image_url(self, obj: PortfolioImage) -> str:
        return build_media_url(obj.image, self.context.get("request"))


class PublicServiceProviderListSerializer(serializers.ModelSerializer):
    trades = serializers.SerializerMethodField()
    primary_trade = serializers.SerializerMethodField()
    service_areas = ServiceAreaSerializer(many=True, read_only=True)
    display_location = serializers.CharField(source="public_display_location", read_only=True)
    verification_badges = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    portfolio_count = serializers.SerializerMethodField()
    review_trust_signals = serializers.SerializerMethodField()

    class Meta:
        model = ServiceProvider
        fields = [
            "id",
            "slug",
            "provider_type",
            "business_name",
            "headline",
            "biography",
            "phone",
            "email",
            "country",
            "state",
            "city",
            "lga",
            "neighborhood",
            "display_location",
            "verification_badges",
            "review_trust_signals",
            "average_rating",
            "published_review_count",
            "recommendation_percentage",
            "completed_jobs_count",
            "trades",
            "primary_trade",
            "service_areas",
            "cover_image_url",
            "portfolio_count",
            "created_at",
        ]
        read_only_fields = fields

    def _active_trades(self, obj):
        return [
            trade
            for trade in obj.trades.all()
            if trade.status == ProviderTradeStatus.ACTIVE
            and trade.category.is_active
            and not trade.category.deleted_at
        ]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_trades(self, obj):
        return ProviderTradeSerializer(
            self._active_trades(obj),
            many=True,
            context=self.context,
        ).data

    @extend_schema_field(serializers.DictField(allow_null=True))
    def get_primary_trade(self, obj):
        primary = next((trade for trade in self._active_trades(obj) if trade.is_primary), None)
        return ProviderTradeSerializer(primary, context=self.context).data if primary else None

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_verification_badges(self, obj):
        snapshot = obj.verification_snapshot or {}
        badges = snapshot.get("badges", [])
        if isinstance(badges, list):
            return badges
        return []

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_review_trust_signals(self, obj):
        from apps.services.services import build_review_trust_signals

        return build_review_trust_signals(obj)

    def get_cover_image_url(self, obj: ServiceProvider) -> str:
        image = next(
            (
                item
                for item in obj.portfolio_images.all()
                if item.is_cover and item.status == PortfolioImageStatus.ACTIVE
            ),
            None,
        )
        return build_media_url(image.image, self.context.get("request")) if image else ""

    def get_portfolio_count(self, obj: ServiceProvider) -> int:
        return len(
            [
                item
                for item in obj.portfolio_images.all()
                if item.status == PortfolioImageStatus.ACTIVE and not item.deleted_at
            ]
        )


class PublicServiceProviderDetailSerializer(PublicServiceProviderListSerializer):
    portfolio = serializers.SerializerMethodField()
    reviews_summary = serializers.SerializerMethodField()

    class Meta(PublicServiceProviderListSerializer.Meta):
        fields = PublicServiceProviderListSerializer.Meta.fields + [
            "portfolio",
            "reviews_summary",
        ]

    @extend_schema_field(serializers.DictField())
    def get_portfolio(self, obj):
        items = [
            item
            for item in obj.portfolio_images.all()
            if item.status == PortfolioImageStatus.ACTIVE and not item.deleted_at
        ]
        return {
            "items": PortfolioImagePublicSerializer(
                items,
                many=True,
                context=self.context,
            ).data,
            "message": (
                "Portfolio images are supplied by the provider and remain subject to "
                "RealityNG moderation."
            ),
        }

    @extend_schema_field(serializers.DictField())
    def get_reviews_summary(self, obj):
        return {
            "average_rating": str(obj.average_rating),
            "average_quality_rating": str(obj.average_quality_rating),
            "average_punctuality_rating": str(obj.average_punctuality_rating),
            "average_communication_rating": str(obj.average_communication_rating),
            "average_value_rating": str(obj.average_value_rating),
            "completed_jobs_count": obj.completed_jobs_count,
            "review_count": obj.published_review_count,
            "recommendation_percentage": obj.recommendation_percentage,
            "message": (
                "Ratings are calculated from published reviews linked to completed "
                "RealityNG service engagements."
            ),
        }


class ServiceProviderOwnerSerializer(serializers.ModelSerializer):
    trades = ProviderTradeSerializer(many=True, read_only=True)
    service_areas = ServiceAreaSerializer(many=True, read_only=True)
    portfolio_count = serializers.SerializerMethodField()
    completion = serializers.SerializerMethodField()

    class Meta:
        model = ServiceProvider
        fields = [
            "id",
            "slug",
            "provider_type",
            "business_name",
            "headline",
            "biography",
            "phone",
            "email",
            "country",
            "state",
            "city",
            "lga",
            "neighborhood",
            "private_address",
            "display_location",
            "verification_snapshot",
            "average_rating",
            "completed_jobs_count",
            "status",
            "published_at",
            "submitted_at",
            "reviewed_at",
            "review_notes",
            "rejection_reason",
            "more_info_message",
            "suspended_reason",
            "warning_count",
            "last_warning_reason",
            "suspension_type",
            "suspension_expires_at",
            "appeal_status",
            "trades",
            "service_areas",
            "portfolio_count",
            "completion",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "verification_snapshot",
            "average_rating",
            "completed_jobs_count",
            "status",
            "published_at",
            "submitted_at",
            "reviewed_at",
            "review_notes",
            "rejection_reason",
            "more_info_message",
            "suspended_reason",
            "warning_count",
            "last_warning_reason",
            "suspension_type",
            "suspension_expires_at",
            "appeal_status",
            "trades",
            "service_areas",
            "portfolio_count",
            "completion",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.DictField())
    def get_completion(self, obj):
        return validate_provider_submission(obj)

    def get_portfolio_count(self, obj) -> int:
        return obj.portfolio_images.count()

    def validate(self, attrs: dict) -> dict:
        instance = self.instance
        if instance and instance.status == ProviderStatus.PENDING_REVIEW:
            raise serializers.ValidationError(
                {"status": ["Profiles under review cannot be edited until reviewed."]}
            )
        if instance and instance.status == ProviderStatus.SUSPENDED:
            raise serializers.ValidationError(
                {"status": ["Suspended profiles cannot be edited. Contact support."]}
            )
        if instance and instance.status == ProviderStatus.ACTIVE:
            sensitive = set(attrs) & MODERATION_SENSITIVE_FIELDS
            if sensitive:
                raise serializers.ValidationError(
                    {
                        "fields": [
                            "This active-profile field requires moderation before editing."
                        ],
                    }
                )
        return attrs


class ProviderTradeWriteSerializer(serializers.ModelSerializer):
    category_id = serializers.UUIDField(write_only=True)
    category = TradeCategorySerializer(read_only=True)

    class Meta:
        model = ProviderTrade
        fields = [
            "id",
            "category",
            "category_id",
            "is_primary",
            "years_experience",
            "skill_level",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "category", "status", "created_at", "updated_at"]

    def validate_category_id(self, value):
        try:
            category = TradeCategory.objects.get(id=value, is_active=True)
        except TradeCategory.DoesNotExist as exc:
            raise serializers.ValidationError("Select an active service category.") from exc
        self.context["category"] = category
        return value

    def validate(self, attrs):
        provider = self.context["provider"]
        category = self.context.get("category") or getattr(self.instance, "category", None)
        if self.instance is None and category:
            if ProviderTrade.objects.filter(provider=provider, category=category).exists():
                raise serializers.ValidationError(
                    {"category_id": ["This category is already selected."]}
                )
        return attrs

    def create(self, validated_data):
        validated_data.pop("category_id", None)
        return ProviderTrade.objects.create(
            provider=self.context["provider"],
            category=self.context["category"],
            **validated_data,
        )

    def update(self, instance, validated_data):
        if "category_id" in validated_data:
            validated_data.pop("category_id", None)
            instance.category = self.context["category"]
        return super().update(instance, validated_data)


class ServiceAreaWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceArea
        fields = [
            "id",
            "country",
            "state",
            "city",
            "lga",
            "neighborhood",
            "service_radius_km",
            "is_primary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_service_radius_km(self, value):
        if value is not None and (value < 1 or value > 100):
            raise serializers.ValidationError("Service radius must be between 1 and 100km.")
        return value


class PortfolioImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    image = serializers.ImageField(write_only=True, required=True)
    category = TradeCategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = PortfolioImage
        fields = [
            "id",
            "image",
            "image_url",
            "caption",
            "category",
            "category_id",
            "display_order",
            "is_cover",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "image_url", "status", "created_at", "updated_at"]

    def get_image_url(self, obj: PortfolioImage) -> str:
        return build_media_url(obj.image, self.context.get("request"))

    def validate_category_id(self, value):
        if value is None:
            return value
        try:
            category = TradeCategory.objects.get(id=value, is_active=True)
        except TradeCategory.DoesNotExist as exc:
            raise serializers.ValidationError("Select an active service category.") from exc
        self.context["category"] = category
        return value

    def validate_image(self, value):
        allowed_types = set(settings.SERVICE_PORTFOLIO_IMAGE_ALLOWED_TYPES)
        content_type = getattr(value, "content_type", "")
        if content_type not in allowed_types:
            allowed = ", ".join(sorted(allowed_types))
            raise serializers.ValidationError(f"Image must be one of: {allowed}.")

        allowed_extensions = {
            extension.lower() for extension in settings.SERVICE_PORTFOLIO_IMAGE_ALLOWED_EXTENSIONS
        }
        extension = Path(value.name).suffix.lower()
        if extension not in allowed_extensions:
            allowed = ", ".join(sorted(allowed_extensions))
            raise serializers.ValidationError(f"Image extension must be one of: {allowed}.")

        max_size = settings.SERVICE_PORTFOLIO_IMAGE_MAX_SIZE_MB * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Image must be {settings.SERVICE_PORTFOLIO_IMAGE_MAX_SIZE_MB}MB or smaller."
            )

        try:
            image = Image.open(value)
            image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise serializers.ValidationError("Uploaded file must be a valid image.") from exc
        finally:
            value.seek(0)
        return value

    def validate(self, attrs):
        provider = self.context["provider"]
        image_count = provider.portfolio_images.count()
        if self.instance is None and image_count >= settings.SERVICE_PORTFOLIO_IMAGE_MAX_COUNT:
            raise serializers.ValidationError(
                {
                    "image": [
                        f"A provider can have at most "
                        f"{settings.SERVICE_PORTFOLIO_IMAGE_MAX_COUNT} portfolio images."
                    ]
                }
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("category_id", None)
        if "category" in self.context:
            validated_data["category"] = self.context["category"]
        provider = self.context["provider"]
        if not provider.portfolio_images.exists():
            validated_data["is_cover"] = True
        return PortfolioImage.objects.create(provider=provider, **validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("image", None)
        if "category_id" in validated_data:
            validated_data.pop("category_id", None)
            instance.category = self.context.get("category")
        return super().update(instance, validated_data)


class PortfolioImageMetadataSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    category = TradeCategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = PortfolioImage
        fields = [
            "id",
            "image_url",
            "caption",
            "category",
            "category_id",
            "display_order",
            "is_cover",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "image_url", "status", "created_at", "updated_at"]

    def get_image_url(self, obj: PortfolioImage) -> str:
        return build_media_url(obj.image, self.context.get("request"))

    def validate_category_id(self, value):
        if value is None:
            return value
        try:
            category = TradeCategory.objects.get(id=value, is_active=True)
        except TradeCategory.DoesNotExist as exc:
            raise serializers.ValidationError("Select an active service category.") from exc
        self.context["category"] = category
        return value

    def update(self, instance, validated_data):
        if "category_id" in validated_data:
            validated_data.pop("category_id", None)
            instance.category = self.context.get("category")
        return super().update(instance, validated_data)


class PortfolioReorderSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )

    def validate_items(self, value):
        for item in value:
            if "id" not in item or "display_order" not in item:
                raise serializers.ValidationError("Each item needs id and display_order.")
        return value


class AdminServiceProviderSerializer(ServiceProviderOwnerSerializer):
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True)

    class Meta(ServiceProviderOwnerSerializer.Meta):
        fields = ServiceProviderOwnerSerializer.Meta.fields + ["reviewed_by_email"]
        read_only_fields = ServiceProviderOwnerSerializer.Meta.read_only_fields + [
            "reviewed_by_email"
        ]


class AdminDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)
    review_notes = serializers.CharField(required=False, allow_blank=True)
    suspension_type = serializers.ChoiceField(
        choices=ProviderSuspensionType.choices,
        required=False,
        default=ProviderSuspensionType.TEMPORARY,
    )
    suspension_expires_at = serializers.DateTimeField(required=False, allow_null=True)


class QuoteProviderSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceProvider
        fields = ["id", "slug", "business_name", "provider_type", "display_location"]
        read_only_fields = fields


class QuoteRequestSerializer(serializers.ModelSerializer):
    provider = QuoteProviderSummarySerializer(read_only=True)
    service_category = TradeCategorySerializer(read_only=True)
    customer_email = serializers.EmailField(source="customer.email", read_only=True)

    class Meta:
        model = QuoteRequest
        fields = [
            "id",
            "customer",
            "customer_name",
            "customer_email",
            "provider",
            "service_category",
            "project_title",
            "project_description",
            "budget_range",
            "preferred_contact_method",
            "phone",
            "email",
            "property_address",
            "state",
            "lga",
            "preferred_start_date",
            "status",
            "viewed_at",
            "responded_at",
            "closed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class QuoteRequestCreateSerializer(serializers.ModelSerializer):
    provider_slug = serializers.CharField(write_only=True)
    service_category_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    customer_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    class Meta:
        model = QuoteRequest
        fields = [
            "provider_slug",
            "service_category_id",
            "customer_name",
            "project_title",
            "project_description",
            "budget_range",
            "preferred_contact_method",
            "phone",
            "email",
            "property_address",
            "state",
            "lga",
            "preferred_start_date",
        ]

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        provider_slug = attrs.pop("provider_slug")
        try:
            provider = active_public_provider_queryset().get(slug=provider_slug)
        except ServiceProvider.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"provider_slug": ["This provider is not available for quote requests."]}
            ) from exc

        category_id = attrs.pop("service_category_id", None)
        category = None
        if category_id:
            category = TradeCategory.objects.filter(id=category_id, is_active=True).first()
            if not category:
                raise serializers.ValidationError(
                    {"service_category_id": ["Select an active service category."]}
                )
            has_category = provider.trades.filter(
                category=category,
                status=ProviderTradeStatus.ACTIVE,
            ).exists()
            if not has_category:
                raise serializers.ValidationError(
                    {
                        "service_category_id": [
                            "This provider has not listed that service category."
                        ]
                    }
                )

        if not user or not user.is_authenticated:
            required = ["customer_name", "phone", "email"]
            missing = [field for field in required if not attrs.get(field)]
            if missing:
                raise serializers.ValidationError(
                    {
                        field: ["This field is required for anonymous quote requests."]
                        for field in missing
                    }
                )
        else:
            attrs["customer_name"] = attrs.get("customer_name") or user.full_name or user.email
            attrs["phone"] = attrs.get("phone") or user.phone_number or ""
            attrs["email"] = attrs.get("email") or user.email

        if attrs.get("preferred_contact_method") not in PreferredContactMethod.values:
            raise serializers.ValidationError(
                {"preferred_contact_method": ["Select a valid contact method."]}
            )
        if not attrs.get("phone") and attrs.get("preferred_contact_method") in [
            PreferredContactMethod.PHONE,
            PreferredContactMethod.WHATSAPP,
        ]:
            raise serializers.ValidationError(
                {"phone": ["Phone is required for phone or WhatsApp contact."]}
            )

        attrs["provider"] = provider
        attrs["service_category"] = category
        attrs["customer"] = user if user and user.is_authenticated else None
        return attrs

    def create(self, validated_data):
        return QuoteRequest.objects.create(**validated_data)


class QuoteRequestStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=QuoteRequestStatus.choices)


class ServiceBookingSummarySerializer(serializers.ModelSerializer):
    provider = QuoteProviderSummarySerializer(read_only=True)
    service_category = TradeCategorySerializer(read_only=True)

    class Meta:
        model = ServiceBooking
        fields = [
            "id",
            "provider",
            "title",
            "service_summary",
            "status",
            "service_category",
            "completed_at",
            "created_at",
        ]
        read_only_fields = fields


class ServiceReviewPublicSerializer(serializers.ModelSerializer):
    reviewer_label = serializers.SerializerMethodField()
    booking = ServiceBookingSummarySerializer(read_only=True)

    class Meta:
        model = ServiceReview
        fields = [
            "id",
            "reviewer_label",
            "booking",
            "rating",
            "title",
            "comment",
            "would_recommend",
            "quality_rating",
            "punctuality_rating",
            "communication_rating",
            "value_rating",
            "provider_response",
            "provider_responded_at",
            "published_at",
            "created_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField())
    def get_reviewer_label(self, obj) -> str:
        first_name = (obj.customer.first_name or "").strip()
        if first_name:
            return f"{first_name[:1]}. Verified customer"
        return "Verified customer"


class ServiceReviewSerializer(ServiceReviewPublicSerializer):
    provider = QuoteProviderSummarySerializer(read_only=True)
    status = serializers.CharField(read_only=True)
    can_edit = serializers.SerializerMethodField()

    class Meta(ServiceReviewPublicSerializer.Meta):
        fields = ServiceReviewPublicSerializer.Meta.fields + [
            "customer",
            "provider",
            "status",
            "can_edit",
            "updated_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.BooleanField())
    def get_can_edit(self, obj) -> bool:
        edit_deadline = obj.created_at + timedelta(
            hours=getattr(settings, "SERVICE_REVIEW_EDIT_WINDOW_HOURS", 48)
        )
        return obj.status == ServiceReviewStatus.PENDING and timezone.now() <= edit_deadline


class ServiceReviewCreateSerializer(serializers.ModelSerializer):
    booking_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = ServiceReview
        fields = [
            "booking_id",
            "rating",
            "title",
            "comment",
            "would_recommend",
            "quality_rating",
            "punctuality_rating",
            "communication_rating",
            "value_rating",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        booking_id = attrs.pop("booking_id")
        try:
            booking = ServiceBooking.objects.select_related(
                "customer",
                "provider",
                "service_category",
            ).get(id=booking_id, customer=request.user)
        except ServiceBooking.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"booking_id": ["This completed booking is not available for review."]}
            ) from exc

        if not booking.is_review_eligible:
            raise serializers.ValidationError(
                {"booking_id": ["Only completed service bookings can be reviewed."]}
            )
        if booking.provider.user_id == request.user.id:
            raise serializers.ValidationError(
                {"booking_id": ["Providers cannot review themselves."]}
            )
        if booking.provider.status != ProviderStatus.ACTIVE:
            raise serializers.ValidationError(
                {"provider": ["This provider is not currently eligible for reviews."]}
            )
        if ServiceReview.objects.filter(booking=booking).exists():
            raise serializers.ValidationError(
                {"booking_id": ["A review already exists for this booking."]}
            )
        self._reject_unsafe_text(attrs.get("title", ""), "title")
        self._reject_unsafe_text(attrs.get("comment", ""), "comment")
        attrs["booking"] = booking
        attrs["customer"] = request.user
        attrs["provider"] = booking.provider
        return attrs

    def validate_rating(self, value):
        return self._validate_rating(value, "rating")

    def validate_quality_rating(self, value):
        return self._validate_optional_rating(value, "quality_rating")

    def validate_punctuality_rating(self, value):
        return self._validate_optional_rating(value, "punctuality_rating")

    def validate_communication_rating(self, value):
        return self._validate_optional_rating(value, "communication_rating")

    def validate_value_rating(self, value):
        return self._validate_optional_rating(value, "value_rating")

    def _validate_optional_rating(self, value, field_name):
        if value is None:
            return value
        return self._validate_rating(value, field_name)

    def _validate_rating(self, value, field_name):
        if not 1 <= value <= 5:
            raise serializers.ValidationError(f"{field_name} must be between 1 and 5.")
        return value

    def _reject_unsafe_text(self, value: str, field_name: str) -> None:
        if "<" in value or ">" in value:
            raise serializers.ValidationError({field_name: ["HTML is not allowed."]})


class ServiceReviewUpdateSerializer(ServiceReviewCreateSerializer):
    booking_id = serializers.UUIDField(write_only=True, required=False)

    class Meta(ServiceReviewCreateSerializer.Meta):
        fields = [
            "rating",
            "title",
            "comment",
            "would_recommend",
            "quality_rating",
            "punctuality_rating",
            "communication_rating",
            "value_rating",
        ]

    def validate(self, attrs):
        self._reject_unsafe_text(attrs.get("title", ""), "title")
        self._reject_unsafe_text(attrs.get("comment", ""), "comment")
        return attrs


class ProviderReviewResponseSerializer(serializers.Serializer):
    response = serializers.CharField(min_length=2, max_length=800)

    def validate_response(self, value):
        if "<" in value or ">" in value:
            raise serializers.ValidationError("HTML is not allowed.")
        return value.strip()


class ServiceReviewFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceReviewFlag
        fields = ["reason", "details"]

    def validate_reason(self, value):
        if value not in ServiceReviewFlagReason.values:
            raise serializers.ValidationError("Select a supported flag reason.")
        return value

    def validate_details(self, value):
        if "<" in value or ">" in value:
            raise serializers.ValidationError("HTML is not allowed.")
        return value


class AdminReviewDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class AdminServiceReviewSerializer(ServiceReviewSerializer):
    flags = ServiceReviewFlagSerializer(many=True, read_only=True)
    moderation_reason = serializers.CharField(read_only=True)
    creation_ip = serializers.IPAddressField(read_only=True)
    user_agent = serializers.CharField(read_only=True)
    risk_flags = serializers.JSONField(read_only=True)

    class Meta(ServiceReviewSerializer.Meta):
        fields = ServiceReviewSerializer.Meta.fields + [
            "moderation_reason",
            "creation_ip",
            "user_agent",
            "risk_flags",
            "flags",
        ]
        read_only_fields = fields


class ServiceComplaintEvidenceSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ServiceComplaintEvidence
        fields = [
            "id",
            "file",
            "file_url",
            "caption",
            "uploaded_by",
            "uploaded_by_email",
            "created_at",
        ]
        read_only_fields = ["id", "file_url", "uploaded_by", "uploaded_by_email", "created_at"]

    def get_file_url(self, obj: ServiceComplaintEvidence) -> str:
        request = self.context.get("request")
        return build_media_url(obj.file, request)


class ServiceComplaintSerializer(serializers.ModelSerializer):
    provider = QuoteProviderSummarySerializer(read_only=True)
    evidence = ServiceComplaintEvidenceSerializer(many=True, read_only=True)
    complainant_email = serializers.EmailField(source="complainant.email", read_only=True)
    assigned_admin_email = serializers.EmailField(source="assigned_admin.email", read_only=True)

    class Meta:
        model = ServiceComplaint
        fields = [
            "id",
            "complainant",
            "complainant_email",
            "provider",
            "quote_request",
            "review",
            "booking",
            "complaint_type",
            "category",
            "subject",
            "description",
            "status",
            "assigned_admin",
            "assigned_admin_email",
            "resolution_notes",
            "resolved_at",
            "rejected_at",
            "escalated_at",
            "closed_at",
            "evidence",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "complainant",
            "complainant_email",
            "provider",
            "status",
            "assigned_admin",
            "assigned_admin_email",
            "resolution_notes",
            "resolved_at",
            "rejected_at",
            "escalated_at",
            "closed_at",
            "evidence",
            "created_at",
            "updated_at",
        ]


class AdminServiceComplaintSerializer(ServiceComplaintSerializer):
    admin_notes = serializers.CharField(read_only=True)

    class Meta(ServiceComplaintSerializer.Meta):
        fields = ServiceComplaintSerializer.Meta.fields + ["admin_notes"]
        read_only_fields = ServiceComplaintSerializer.Meta.read_only_fields + ["admin_notes"]


class ServiceComplaintCreateSerializer(serializers.ModelSerializer):
    provider_id = serializers.UUIDField(write_only=True)
    quote_request_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    review_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)
    booking_id = serializers.UUIDField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = ServiceComplaint
        fields = [
            "provider_id",
            "quote_request_id",
            "review_id",
            "booking_id",
            "complaint_type",
            "category",
            "subject",
            "description",
        ]

    def validate(self, attrs):
        request = self.context["request"]
        provider_id = attrs.pop("provider_id")
        provider = ServiceProvider.objects.filter(id=provider_id).first()
        if not provider:
            raise serializers.ValidationError({"provider_id": ["Provider was not found."]})
        if attrs.get("complaint_type") not in ServiceComplaintType.values:
            raise serializers.ValidationError({"complaint_type": ["Select a valid type."]})
        if attrs.get("category") not in ServiceComplaintCategory.values:
            raise serializers.ValidationError({"category": ["Select a valid category."]})
        if "<" in attrs.get("subject", "") or ">" in attrs.get("subject", ""):
            raise serializers.ValidationError({"subject": ["HTML is not allowed."]})
        if "<" in attrs.get("description", "") or ">" in attrs.get("description", ""):
            raise serializers.ValidationError({"description": ["HTML is not allowed."]})

        quote_request_id = attrs.pop("quote_request_id", None)
        review_id = attrs.pop("review_id", None)
        booking_id = attrs.pop("booking_id", None)
        if quote_request_id:
            quote_request = QuoteRequest.objects.filter(id=quote_request_id).first()
            if not quote_request or quote_request.provider_id != provider.id:
                raise serializers.ValidationError(
                    {"quote_request_id": ["Quote request does not match this provider."]}
                )
            if quote_request.customer_id and quote_request.customer_id != request.user.id:
                if quote_request.provider.user_id != request.user.id:
                    raise serializers.ValidationError(
                        {"quote_request_id": ["You cannot complain about this quote request."]}
                    )
            attrs["quote_request"] = quote_request
        if review_id:
            review = ServiceReview.objects.filter(id=review_id).first()
            if not review or review.provider_id != provider.id:
                raise serializers.ValidationError(
                    {"review_id": ["Review does not match this provider."]}
                )
            if review.customer_id != request.user.id and review.provider.user_id != request.user.id:
                raise serializers.ValidationError(
                    {"review_id": ["You cannot complain about this review."]}
                )
            attrs["review"] = review
        if booking_id:
            booking = ServiceBooking.objects.filter(id=booking_id).first()
            if not booking or booking.provider_id != provider.id:
                raise serializers.ValidationError(
                    {"booking_id": ["Booking does not match this provider."]}
                )
            if (
                booking.customer_id != request.user.id
                and booking.provider.user_id != request.user.id
            ):
                raise serializers.ValidationError(
                    {"booking_id": ["You cannot complain about this booking."]}
                )
            attrs["booking"] = booking

        if provider.user_id == request.user.id:
            attrs["complaint_type"] = ServiceComplaintType.PROVIDER
        attrs["provider"] = provider
        attrs["complainant"] = request.user
        return attrs


class AdminComplaintDecisionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ServiceComplaintStatus.choices, required=False)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=1600)
    admin_notes = serializers.CharField(required=False, allow_blank=True, max_length=1600)


class ProviderAppealSerializer(serializers.ModelSerializer):
    provider = QuoteProviderSummarySerializer(read_only=True)
    submitted_by_email = serializers.EmailField(source="submitted_by.email", read_only=True)
    decided_by_email = serializers.EmailField(source="decided_by.email", read_only=True)

    class Meta:
        model = ProviderAppeal
        fields = [
            "id",
            "provider",
            "submitted_by",
            "submitted_by_email",
            "appeal_type",
            "reason",
            "status",
            "admin_notes",
            "decided_by",
            "decided_by_email",
            "decided_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "provider",
            "submitted_by",
            "submitted_by_email",
            "status",
            "admin_notes",
            "decided_by",
            "decided_by_email",
            "decided_at",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        provider = self.context["provider"]
        appeal_type = attrs.get("appeal_type")
        if appeal_type not in ProviderAppealType.values:
            raise serializers.ValidationError({"appeal_type": ["Select a valid appeal type."]})
        if (
            appeal_type == ProviderAppealType.SUSPENSION
            and provider.status != ProviderStatus.SUSPENDED
        ):
            raise serializers.ValidationError(
                {"appeal_type": ["Only suspended providers can submit a suspension appeal."]}
            )
        if appeal_type == ProviderAppealType.WARNING and not provider.warning_count:
            raise serializers.ValidationError(
                {"appeal_type": ["A warning must exist before it can be appealed."]}
            )
        open_appeal = ProviderAppeal.objects.filter(
            provider=provider,
            appeal_type=appeal_type,
            status__in=[
                ProviderAppealStatus.SUBMITTED,
                ProviderAppealStatus.UNDER_REVIEW,
                ProviderAppealStatus.REOPENED,
            ],
        ).exists()
        if open_appeal:
            raise serializers.ValidationError(
                {"appeal_type": ["There is already an open appeal for this action."]}
            )
        if "<" in attrs.get("reason", "") or ">" in attrs.get("reason", ""):
            raise serializers.ValidationError({"reason": ["HTML is not allowed."]})
        return attrs


class AdminAppealDecisionSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, max_length=1600)


class ServicesDashboardStatSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.CharField()
    detail = serializers.CharField(required=False, allow_blank=True)
    tone = serializers.CharField(required=False, allow_blank=True)


class ServicesDashboardActivityItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(required=False, allow_blank=True)
    timestamp = serializers.DateTimeField()
    href = serializers.CharField(required=False, allow_blank=True)


class ServicesDashboardBreakdownItemSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.IntegerField()


class CustomerServicesDashboardSerializer(serializers.Serializer):
    stats = ServicesDashboardStatSerializer(many=True)
    recent_quote_requests = QuoteRequestSerializer(many=True)
    submitted_reviews = ServiceReviewSerializer(many=True)
    eligible_reviews = ServiceBookingSummarySerializer(many=True)
    recent_providers = PublicServiceProviderListSerializer(many=True)
    recommended_providers = PublicServiceProviderListSerializer(many=True)
    service_categories = TradeCategorySerializer(many=True)
    activity = ServicesDashboardActivityItemSerializer(many=True)


class ProviderServicesDashboardSerializer(serializers.Serializer):
    profile = ServiceProviderOwnerSerializer(allow_null=True)
    stats = ServicesDashboardStatSerializer(many=True)
    quote_status_counts = serializers.DictField(child=serializers.IntegerField())
    review_status_counts = serializers.DictField(child=serializers.IntegerField())
    recent_quote_requests = QuoteRequestSerializer(many=True)
    latest_reviews = ServiceReviewSerializer(many=True)
    response_reminders = ServiceReviewSerializer(many=True)
    activity = ServicesDashboardActivityItemSerializer(many=True)


class AdminServicesDashboardSerializer(serializers.Serializer):
    stats = ServicesDashboardStatSerializer(many=True)
    provider_status_counts = serializers.DictField(child=serializers.IntegerField())
    quote_status_counts = serializers.DictField(child=serializers.IntegerField())
    review_status_counts = serializers.DictField(child=serializers.IntegerField())
    pending_providers = AdminServiceProviderSerializer(many=True)
    pending_reviews = AdminServiceReviewSerializer(many=True)
    flagged_reviews = AdminServiceReviewSerializer(many=True)
    open_quote_requests = QuoteRequestSerializer(many=True)
    category_breakdown = ServicesDashboardBreakdownItemSerializer(many=True)
    geographic_breakdown = ServicesDashboardBreakdownItemSerializer(many=True)
    activity = ServicesDashboardActivityItemSerializer(many=True)


def validate_provider_submission(provider: ServiceProvider) -> dict:
    missing: list[str] = []
    if not provider.provider_type:
        missing.append("provider_type")
    if not provider.business_name:
        missing.append("business_name")
    if not provider.headline:
        missing.append("headline")
    if not provider.biography:
        missing.append("biography")
    if not provider.phone and not provider.email:
        missing.append("contact")
    if not provider.trades.filter(status=ProviderTradeStatus.ACTIVE, is_primary=True).exists():
        missing.append("primary_trade")
    if not provider.service_areas.exists():
        missing.append("service_area")

    return {
        "is_complete": not missing,
        "missing": missing,
        "message": (
            "Profile is ready for review."
            if not missing
            else "Complete the missing items before submitting."
        ),
    }


def active_public_provider_queryset():
    return (
        ServiceProvider.objects.filter(status=ProviderStatus.ACTIVE)
        .select_related("user")
        .prefetch_related("trades__category", "service_areas", "portfolio_images__category")
    )
