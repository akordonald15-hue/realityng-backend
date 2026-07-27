"""Serializers for verification requests, documents, and property verifications."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from apps.trust.models import PropertyVerification, VerificationDocument, VerificationRequest
from apps.trust.validators import (
    compute_checksum,
    sanitize_original_filename,
    validate_verification_document,
)


def build_verification_document_url(file_field, request=None) -> str:
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


class VerificationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerificationDocument
        fields = (
            "id",
            "verification_request",
            "document_type",
            "file",
            "original_filename",
            "mime_type",
            "file_size",
            "reviewed_status",
            "uploaded_at",
        )
        read_only_fields = (
            "id",
            "verification_request",
            "original_filename",
            "mime_type",
            "file_size",
            "reviewed_status",
            "uploaded_at",
        )

    def validate_file(self, value):
        try:
            validate_verification_document(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message) from exc
        return value

    def to_representation(self, instance: VerificationDocument) -> dict:
        data = super().to_representation(instance)
        data["file"] = build_verification_document_url(
            instance.file,
            self.context.get("request"),
        )
        return data

    def create(self, validated_data: dict) -> VerificationDocument:
        file_obj = validated_data["file"]
        validated_data["original_filename"] = sanitize_original_filename(file_obj.name)
        validated_data["mime_type"] = getattr(file_obj, "content_type", "")
        validated_data["file_size"] = file_obj.size
        validated_data["checksum"] = compute_checksum(file_obj)
        return super().create(validated_data)


class VerificationRequestSerializer(serializers.ModelSerializer):
    """Self-service view: excludes review_notes, an admin-internal field."""

    documents = VerificationDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = VerificationRequest
        fields = (
            "id",
            "user",
            "verification_type",
            "status",
            "business_name",
            "cac_registration_number",
            "trade_category",
            "years_experience",
            "phone_number",
            "contact_address",
            "city",
            "submitted_at",
            "reviewed_at",
            "reviewer",
            "rejection_reason",
            "expiry_date",
            "documents",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "status",
            "submitted_at",
            "reviewed_at",
            "reviewer",
            "rejection_reason",
            "expiry_date",
            "created_at",
            "updated_at",
        )

    def create(self, validated_data: dict) -> VerificationRequest:
        validated_data["user"] = self.context["request"].user
        validated_data["submitted_at"] = timezone.now()
        return super().create(validated_data)


class AdminVerificationRequestSerializer(serializers.ModelSerializer):
    """Admin view: full fields including internal review_notes."""

    documents = VerificationDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = VerificationRequest
        fields = "__all__"


class VerificationDecisionSerializer(serializers.Serializer):
    """Input payload for admin approve/reject/suspend/expire/request-info actions."""

    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")
    review_notes = serializers.CharField(required=False, allow_blank=True, default="")
    expiry_date = serializers.DateField(required=False, allow_null=True, default=None)


class PropertyVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyVerification
        fields = (
            "id",
            "property",
            "submitted_by",
            "status",
            "reviewer",
            "ownership_evidence",
            "location_evidence",
            "inspection_evidence",
            "submitted_at",
            "reviewed_at",
            "rejection_reason",
            "expiry_date",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "submitted_by",
            "status",
            "reviewer",
            "reviewed_at",
            "rejection_reason",
            "expiry_date",
            "created_at",
            "updated_at",
        )

    def validate_property(self, value):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            raise serializers.ValidationError("Authentication is required.")
        if not (user.is_staff or value.owner_id == user.id):
            raise serializers.ValidationError(
                "Only the property owner or an admin can submit property verification."
            )
        return value

    def create(self, validated_data: dict) -> PropertyVerification:
        validated_data["submitted_by"] = self.context["request"].user
        validated_data["submitted_at"] = timezone.now()
        return super().create(validated_data)


class AdminPropertyVerificationSerializer(serializers.ModelSerializer):
    """Admin view: full fields including verified_snapshot."""

    class Meta:
        model = PropertyVerification
        fields = "__all__"
