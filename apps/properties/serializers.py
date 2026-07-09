from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.utils import timezone
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from apps.accounts.services import user_is_admin
from apps.properties.choices import (
    InquiryStatus,
    InquiryType,
    ListingType,
    PropertyStatus,
    PropertyType,
    RentalApplicationStatus,
    ViewingStatus,
)
from apps.properties.models import (
    Favorite,
    Inquiry,
    Property,
    PropertyImage,
    RentalApplication,
    Viewing,
)

PROPERTY_MUTABLE_FIELDS = [
    "title",
    "description",
    "property_type",
    "listing_type",
    "price",
    "currency",
    "country",
    "state",
    "city",
    "address",
    "bedrooms",
    "bathrooms",
    "parking_spaces",
    "land_size",
    "floor_area",
    "featured",
]


def build_media_url(file_field, request=None) -> str:
    if not file_field:
        return ""
    url = file_field.url
    internal_endpoint = getattr(settings, "MINIO_ENDPOINT", "").rstrip("/")
    public_endpoint = getattr(settings, "MINIO_PUBLIC_ENDPOINT", internal_endpoint).rstrip("/")
    if internal_endpoint and public_endpoint and url.startswith(internal_endpoint):
        url = f"{public_endpoint}{url[len(internal_endpoint) :]}"
    if request and url.startswith("/"):
        return request.build_absolute_uri(url)
    return url


class PropertyImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    image = serializers.ImageField(write_only=True, required=True)

    class Meta:
        model = PropertyImage
        fields = [
            "id",
            "image",
            "image_url",
            "caption",
            "display_order",
            "is_cover",
            "created_at",
        ]
        read_only_fields = ["id", "image_url", "created_at"]

    def get_image_url(self, obj: PropertyImage) -> str:
        return build_media_url(obj.image, self.context.get("request"))

    def validate_image(self, value):
        allowed_types = set(settings.PROPERTY_IMAGE_ALLOWED_TYPES)
        content_type = getattr(value, "content_type", "")
        if content_type not in allowed_types:
            allowed = ", ".join(sorted(allowed_types))
            raise serializers.ValidationError(f"Image must be one of: {allowed}.")

        allowed_extensions = {
            extension.lower() for extension in settings.PROPERTY_IMAGE_ALLOWED_EXTENSIONS
        }
        extension = Path(value.name).suffix.lower()
        if extension not in allowed_extensions:
            allowed = ", ".join(sorted(allowed_extensions))
            raise serializers.ValidationError(f"Image extension must be one of: {allowed}.")

        max_size = settings.PROPERTY_IMAGE_MAX_SIZE_MB * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Image must be {settings.PROPERTY_IMAGE_MAX_SIZE_MB}MB or smaller."
            )
        try:
            image = Image.open(value)
            image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise serializers.ValidationError("Uploaded file must be a valid image.") from exc
        finally:
            value.seek(0)
        return value

    def validate(self, attrs: dict) -> dict:
        prop = self.context.get("property")
        if self.instance is None and prop:
            image_count = prop.images.count()
            if image_count >= settings.PROPERTY_IMAGE_MAX_COUNT:
                raise serializers.ValidationError(
                    {
                        "image": (
                            f"A property can have at most "
                            f"{settings.PROPERTY_IMAGE_MAX_COUNT} images."
                        )
                    }
                )
        return attrs

    def create(self, validated_data: dict) -> PropertyImage:
        prop = self.context["property"]
        if not prop.images.exists():
            validated_data["is_cover"] = True
        return PropertyImage.objects.create(property=prop, **validated_data)


class PropertyImageMetadataSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyImage
        fields = ["id", "image_url", "caption", "display_order", "is_cover", "created_at"]
        read_only_fields = ["id", "image_url", "created_at"]

    def get_image_url(self, obj: PropertyImage) -> str:
        return build_media_url(obj.image, self.context.get("request"))

    def update(self, instance: PropertyImage, validated_data: dict) -> PropertyImage:
        instance.caption = validated_data.get("caption", instance.caption)
        instance.display_order = validated_data.get("display_order", instance.display_order)
        if "is_cover" in validated_data:
            instance.is_cover = validated_data["is_cover"]
        instance.save()
        return instance


class PropertySerializer(serializers.ModelSerializer):
    owner_id = serializers.UUIDField(source="owner.id", read_only=True)
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()
    image_gallery = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "property_type",
            "listing_type",
            "price",
            "currency",
            "country",
            "state",
            "city",
            "address",
            "bedrooms",
            "bathrooms",
            "parking_spaces",
            "land_size",
            "floor_area",
            "status",
            "featured",
            "owner_id",
            "owner_email",
            "cover_image_url",
            "image_count",
            "image_gallery",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "status",
            "owner_id",
            "owner_email",
            "cover_image_url",
            "image_count",
            "image_gallery",
            "created_at",
            "updated_at",
        ]

    def get_cover_image_url(self, obj: Property) -> str:
        cover = next((image for image in obj.images.all() if image.is_cover), None)
        return build_media_url(cover.image, self.context.get("request")) if cover else ""

    def get_image_count(self, obj: Property) -> int:
        if hasattr(obj, "image_count_value"):
            return obj.image_count_value
        return obj.images.count()

    def get_image_gallery(self, obj: Property) -> list[dict]:
        return PropertyImageMetadataSerializer(
            obj.images.all(),
            many=True,
            context=self.context,
        ).data

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than zero.")
        return value

    def validate_currency(self, value: str) -> str:
        value = value.upper()
        if len(value) != 3:
            raise serializers.ValidationError("Currency must be a valid 3-letter code.")
        return value

    def validate(self, attrs: dict) -> dict:
        data = {**getattr(self.instance, "__dict__", {}), **attrs}
        missing_location = [
            field
            for field in ["country", "state", "city", "address"]
            if not str(data.get(field) or "").strip()
        ]
        if missing_location:
            raise serializers.ValidationError(
                {field: "This location field is required." for field in missing_location}
            )

        property_type = data.get("property_type")
        listing_type = data.get("listing_type")
        if listing_type == ListingType.APARTMENT_SHARE and property_type != PropertyType.APARTMENT:
            raise serializers.ValidationError(
                {"property_type": "Apartment share listings must use the apartment property type."}
            )

        if property_type == PropertyType.LAND:
            if not data.get("land_size"):
                raise serializers.ValidationError({"land_size": "Land listings require land size."})
        elif not data.get("floor_area"):
            raise serializers.ValidationError(
                {"floor_area": "Built property listings require floor area."}
            )

        return attrs

    def create(self, validated_data: dict) -> Property:
        return Property.objects.create(
            owner=self.context["request"].user,
            status=PropertyStatus.DRAFT,
            **validated_data,
        )

    def update(self, instance: Property, validated_data: dict) -> Property:
        if instance.status == PropertyStatus.APPROVED:
            instance.status = PropertyStatus.DRAFT
        for field in PROPERTY_MUTABLE_FIELDS:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        return instance


class PublicPropertySerializer(serializers.ModelSerializer):
    cover_image_url = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()
    image_gallery = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "property_type",
            "listing_type",
            "price",
            "currency",
            "country",
            "state",
            "city",
            "address",
            "bedrooms",
            "bathrooms",
            "parking_spaces",
            "land_size",
            "floor_area",
            "featured",
            "cover_image_url",
            "image_count",
            "image_gallery",
            "is_favorited",
            "created_at",
        ]

    def get_cover_image_url(self, obj: Property) -> str:
        cover = next((image for image in obj.images.all() if image.is_cover), None)
        return build_media_url(cover.image, self.context.get("request")) if cover else ""

    def get_image_count(self, obj: Property) -> int:
        if hasattr(obj, "image_count_value"):
            return obj.image_count_value
        return obj.images.count()

    def get_image_gallery(self, obj: Property) -> list[dict]:
        return PropertyImageMetadataSerializer(
            obj.images.all(),
            many=True,
            context=self.context,
        ).data

    def get_is_favorited(self, obj: Property) -> bool:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        favorite_property_ids = self.context.get("favorite_property_ids")
        if favorite_property_ids is not None:
            return obj.id in favorite_property_ids

        return Favorite.objects.filter(user=user, property=obj).exists()


class FavoriteSerializer(serializers.ModelSerializer):
    property_id = serializers.UUIDField(write_only=True)
    property = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = ["id", "property_id", "property", "created_at"]
        read_only_fields = ["id", "property", "created_at"]

    def get_property(self, obj: Favorite) -> dict:
        return PublicPropertySerializer(
            obj.property,
            context={
                **self.context,
                "favorite_property_ids": {obj.property_id},
            },
        ).data

    def validate_property_id(self, value):
        try:
            prop = Property.objects.get(id=value)
        except Property.DoesNotExist as exc:
            raise serializers.ValidationError("Property is not available.") from exc

        request = self.context["request"]
        if Favorite.objects.filter(user=request.user, property=prop).exists():
            raise serializers.ValidationError("Property is already saved.")

        self.context["property"] = prop
        return value

    def create(self, validated_data: dict) -> Favorite:
        validated_data.pop("property_id")
        return Favorite.objects.create(
            user=self.context["request"].user,
            property=self.context["property"],
        )


class DashboardSummarySerializer(serializers.Serializer):
    saved_properties_count = serializers.IntegerField()
    active_listings_count = serializers.IntegerField()
    draft_listings_count = serializers.IntegerField()
    my_inquiries_count = serializers.IntegerField(required=False)
    received_inquiries_count = serializers.IntegerField(required=False)
    my_viewings_count = serializers.IntegerField(required=False)
    received_viewings_count = serializers.IntegerField(required=False)
    my_applications_count = serializers.IntegerField(required=False)
    received_applications_count = serializers.IntegerField(required=False)


class DashboardActivityItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    action = serializers.CharField()
    label = serializers.CharField()
    entity_type = serializers.CharField()
    entity_id = serializers.UUIDField()
    property_id = serializers.CharField(allow_blank=True)
    occurred_at = serializers.DateTimeField()


class TransactionItemSerializer(serializers.Serializer):
    property = serializers.DictField()
    stage = serializers.CharField()
    stage_label = serializers.CharField()
    last_update = serializers.DateTimeField()
    next_action = serializers.CharField()
    inquiry_id = serializers.UUIDField(allow_null=True)
    viewing_id = serializers.UUIDField(allow_null=True)
    application_id = serializers.UUIDField(allow_null=True)


class PropertyReviewDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)


class InquiryUserSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    phone_number = serializers.CharField(allow_null=True)


class InquiryPropertySummarySerializer(serializers.ModelSerializer):
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            "id",
            "title",
            "slug",
            "listing_type",
            "property_type",
            "price",
            "currency",
            "city",
            "state",
            "cover_image_url",
        ]

    def get_cover_image_url(self, obj: Property) -> str:
        cover = next((image for image in obj.images.all() if image.is_cover), None)
        return build_media_url(cover.image, self.context.get("request")) if cover else ""


def inquiry_type_for_property(prop: Property) -> str:
    if prop.listing_type == ListingType.SALE:
        return InquiryType.PURCHASE
    if prop.listing_type == ListingType.APARTMENT_SHARE:
        return InquiryType.APARTMENT_SHARE
    return InquiryType.RENT


class InquirySerializer(serializers.ModelSerializer):
    property_id = serializers.UUIDField(write_only=True)
    property = InquiryPropertySummarySerializer(read_only=True)
    interested_user = serializers.SerializerMethodField()
    property_owner = serializers.SerializerMethodField()
    internal_notes = serializers.SerializerMethodField()

    class Meta:
        model = Inquiry
        fields = [
            "id",
            "property_id",
            "property",
            "interested_user",
            "property_owner",
            "inquiry_type",
            "message",
            "contact_preference",
            "status",
            "internal_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "property",
            "interested_user",
            "property_owner",
            "status",
            "internal_notes",
            "created_at",
            "updated_at",
        ]

    def get_interested_user(self, obj: Inquiry) -> dict:
        return InquiryUserSerializer(obj.interested_user).data

    def get_property_owner(self, obj: Inquiry) -> dict:
        return InquiryUserSerializer(obj.property_owner).data

    def get_internal_notes(self, obj: Inquiry) -> str:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated and user.id == obj.property_owner_id:
            return obj.internal_notes
        return ""

    def validate_property_id(self, value):
        try:
            prop = Property.objects.select_related("owner").get(id=value)
        except Property.DoesNotExist as exc:
            raise serializers.ValidationError("Property is not available.") from exc

        if prop.status != PropertyStatus.APPROVED:
            raise serializers.ValidationError("Property is not available for inquiries.")

        request = self.context["request"]
        if prop.owner_id == request.user.id:
            raise serializers.ValidationError("You cannot create an inquiry for your own property.")

        self.context["property"] = prop
        return value

    def validate(self, attrs: dict) -> dict:
        prop = self.context.get("property")
        if not prop:
            return attrs

        expected_type = inquiry_type_for_property(prop)
        inquiry_type = attrs.get("inquiry_type") or expected_type
        if inquiry_type != expected_type:
            raise serializers.ValidationError(
                {"inquiry_type": f"This property accepts {expected_type} inquiries."}
            )
        attrs["inquiry_type"] = inquiry_type
        return attrs

    def create(self, validated_data: dict) -> Inquiry:
        validated_data.pop("property_id")
        prop = self.context["property"]
        return Inquiry.objects.create(
            property=prop,
            interested_user=self.context["request"].user,
            property_owner=prop.owner,
            **validated_data,
        )


class InquiryStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=InquiryStatus.choices)

    def validate_status(self, value: str) -> str:
        inquiry = self.context["inquiry"]
        if value != inquiry.status and not inquiry.can_transition_to(value):
            raise serializers.ValidationError(
                f"Inquiry cannot move from {inquiry.status} to {value}."
            )
        return value


class InquiryNotesSerializer(serializers.Serializer):
    internal_notes = serializers.CharField(allow_blank=True, required=True)


class ViewingSerializer(serializers.ModelSerializer):
    inquiry_id = serializers.UUIDField(write_only=True)
    inquiry = serializers.UUIDField(source="inquiry.id", read_only=True)
    property = InquiryPropertySummarySerializer(read_only=True)
    requester = serializers.SerializerMethodField()
    property_owner = serializers.SerializerMethodField()

    class Meta:
        model = Viewing
        fields = [
            "id",
            "inquiry_id",
            "inquiry",
            "property",
            "requester",
            "property_owner",
            "viewing_type",
            "preferred_date",
            "preferred_time",
            "confirmed_datetime",
            "meeting_location",
            "meeting_link",
            "notes",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "inquiry",
            "property",
            "requester",
            "property_owner",
            "confirmed_datetime",
            "meeting_location",
            "meeting_link",
            "status",
            "created_at",
            "updated_at",
        ]

    def get_requester(self, obj: Viewing) -> dict:
        return InquiryUserSerializer(obj.requester).data

    def get_property_owner(self, obj: Viewing) -> dict:
        return InquiryUserSerializer(obj.property_owner).data

    def validate_inquiry_id(self, value):
        try:
            inquiry = Inquiry.objects.select_related("property", "property__owner").get(id=value)
        except Inquiry.DoesNotExist as exc:
            raise serializers.ValidationError("Inquiry is not available.") from exc

        request = self.context["request"]
        if inquiry.interested_user_id != request.user.id:
            raise serializers.ValidationError(
                "You can only request viewings for your own inquiries."
            )
        if inquiry.status == InquiryStatus.CLOSED:
            raise serializers.ValidationError("Closed inquiries cannot receive viewing requests.")
        if inquiry.property.deleted_at:
            raise serializers.ValidationError("Property is not available for viewing requests.")

        self.context["inquiry"] = inquiry
        return value

    def validate(self, attrs: dict) -> dict:
        preferred_date = attrs.get("preferred_date")
        preferred_time = attrs.get("preferred_time")
        if preferred_date and preferred_date < timezone.localdate():
            raise serializers.ValidationError(
                {"preferred_date": "Preferred date cannot be in the past."}
            )
        if (
            preferred_date
            and preferred_time
            and preferred_date == timezone.localdate()
            and preferred_time <= timezone.localtime().time()
        ):
            raise serializers.ValidationError(
                {"preferred_time": "Preferred time must be in the future."}
            )
        return attrs

    def create(self, validated_data: dict) -> Viewing:
        validated_data.pop("inquiry_id")
        inquiry = self.context["inquiry"]
        return Viewing.objects.create(
            inquiry=inquiry,
            property=inquiry.property,
            requester=self.context["request"].user,
            property_owner=inquiry.property_owner,
            **validated_data,
        )


class ViewingDecisionSerializer(serializers.Serializer):
    confirmed_datetime = serializers.DateTimeField(required=True)
    meeting_location = serializers.CharField(required=False, allow_blank=True)
    meeting_link = serializers.URLField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_confirmed_datetime(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Confirmed viewing time must be in the future.")
        return value


class ViewingNotesSerializer(serializers.Serializer):
    notes = serializers.CharField(allow_blank=True, required=True)


class RentalApplicationSerializer(serializers.ModelSerializer):
    property_id = serializers.UUIDField(write_only=True)
    inquiry_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    viewing_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    property = InquiryPropertySummarySerializer(read_only=True)
    applicant = serializers.SerializerMethodField()
    property_owner = serializers.SerializerMethodField()
    inquiry = serializers.UUIDField(source="inquiry.id", read_only=True)
    viewing = serializers.UUIDField(source="viewing.id", read_only=True)
    owner_notes = serializers.SerializerMethodField()

    class Meta:
        model = RentalApplication
        fields = [
            "id",
            "property_id",
            "property",
            "applicant",
            "property_owner",
            "inquiry_id",
            "inquiry",
            "viewing_id",
            "viewing",
            "full_name",
            "email",
            "phone",
            "employment_status",
            "employer_name",
            "monthly_income",
            "move_in_date",
            "message",
            "status",
            "owner_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "property",
            "applicant",
            "property_owner",
            "inquiry",
            "viewing",
            "status",
            "owner_notes",
            "created_at",
            "updated_at",
        ]

    def get_applicant(self, obj: RentalApplication) -> dict:
        return InquiryUserSerializer(obj.applicant).data

    def get_property_owner(self, obj: RentalApplication) -> dict:
        return InquiryUserSerializer(obj.property_owner).data

    def get_owner_notes(self, obj: RentalApplication) -> str:
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated and (
            user.id == obj.property_owner_id or user_is_admin(user)
        ):
            return obj.owner_notes
        return ""

    def validate_property_id(self, value):
        try:
            prop = Property.objects.select_related("owner").get(id=value)
        except Property.DoesNotExist as exc:
            raise serializers.ValidationError("Property is not available.") from exc

        request = self.context["request"]
        if prop.status != PropertyStatus.APPROVED:
            raise serializers.ValidationError("Property is not available for applications.")
        if prop.owner_id == request.user.id:
            raise serializers.ValidationError("You cannot apply for your own property.")
        if prop.deleted_at:
            raise serializers.ValidationError("Property is not available for applications.")

        self.context["property"] = prop
        return value

    def validate_monthly_income(self, value):
        if value <= 0:
            raise serializers.ValidationError("Monthly income must be greater than zero.")
        return value

    def validate_move_in_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("Move-in date cannot be in the past.")
        return value

    def validate(self, attrs: dict) -> dict:
        prop = self.context.get("property")
        request = self.context["request"]
        inquiry_id = attrs.get("inquiry_id")
        viewing_id = attrs.get("viewing_id")

        if RentalApplication.objects.filter(
            property=prop,
            applicant=request.user,
            status__in=[
                RentalApplicationStatus.SUBMITTED,
                RentalApplicationStatus.UNDER_REVIEW,
                RentalApplicationStatus.APPROVED,
            ],
        ).exists():
            raise serializers.ValidationError(
                "You already have an active application for this property."
            )

        if inquiry_id:
            try:
                inquiry = Inquiry.objects.get(id=inquiry_id)
            except Inquiry.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"inquiry_id": "Inquiry is not available."}
                ) from exc
            if inquiry.interested_user_id != request.user.id or inquiry.property_id != prop.id:
                raise serializers.ValidationError(
                    {"inquiry_id": "Inquiry must belong to this applicant and property."}
                )
            self.context["inquiry"] = inquiry

        if viewing_id:
            try:
                viewing = Viewing.objects.get(id=viewing_id)
            except Viewing.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"viewing_id": "Viewing is not available."}
                ) from exc
            if viewing.requester_id != request.user.id or viewing.property_id != prop.id:
                raise serializers.ValidationError(
                    {"viewing_id": "Viewing must belong to this applicant and property."}
                )
            if viewing.status not in {ViewingStatus.CONFIRMED, ViewingStatus.COMPLETED}:
                raise serializers.ValidationError(
                    {"viewing_id": "Applications can only link confirmed or completed viewings."}
                )
            self.context["viewing"] = viewing
            if "inquiry" not in self.context:
                self.context["inquiry"] = viewing.inquiry

        return attrs

    def create(self, validated_data: dict) -> RentalApplication:
        validated_data.pop("property_id")
        validated_data.pop("inquiry_id", None)
        validated_data.pop("viewing_id", None)
        prop = self.context["property"]
        return RentalApplication.objects.create(
            property=prop,
            applicant=self.context["request"].user,
            property_owner=prop.owner,
            inquiry=self.context.get("inquiry"),
            viewing=self.context.get("viewing"),
            **validated_data,
        )


class RentalApplicationStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=RentalApplicationStatus.choices)

    def validate_status(self, value: str) -> str:
        application = self.context["application"]
        if value != application.status and not application.can_transition_to(value):
            raise serializers.ValidationError(
                f"Application cannot move from {application.status} to {value}."
            )
        return value


class RentalApplicationNotesSerializer(serializers.Serializer):
    owner_notes = serializers.CharField(allow_blank=True, required=True)
