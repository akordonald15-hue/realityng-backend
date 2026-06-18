from __future__ import annotations

from rest_framework import serializers

from apps.properties.choices import PropertyStatus, PropertyType
from apps.properties.models import Property

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


class PropertySerializer(serializers.ModelSerializer):
    owner_id = serializers.UUIDField(source="owner.id", read_only=True)
    owner_email = serializers.EmailField(source="owner.email", read_only=True)

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
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "status",
            "owner_id",
            "owner_email",
            "created_at",
            "updated_at",
        ]

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
            "created_at",
        ]


class PropertyReviewDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)
