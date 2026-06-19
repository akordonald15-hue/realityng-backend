from __future__ import annotations

from django.conf import settings
from rest_framework import serializers

from apps.properties.choices import PropertyStatus, PropertyType
from apps.properties.models import Favorite, Property, PropertyImage

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
        url = f"{public_endpoint}{url[len(internal_endpoint):]}"
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

        max_size = settings.PROPERTY_IMAGE_MAX_SIZE_MB * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Image must be {settings.PROPERTY_IMAGE_MAX_SIZE_MB}MB or smaller."
            )
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
        if property_type == PropertyType.LAND:
            if not data.get("land_size"):
                raise serializers.ValidationError(
                    {"land_size": "Land listings require land size."}
                )
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


class PropertyReviewDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
