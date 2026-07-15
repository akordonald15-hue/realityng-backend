"""Serializers for verification requests, documents, and property verifications."""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.trust.models import PropertyVerification, VerificationDocument, VerificationRequest
from apps.trust.validators import (
    compute_checksum,
    sanitize_original_filename,
    validate_verification_document,
)


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

    def create(self, validated_data: dict) -> VerificationDocument:
        file_obj = validated_data["file"]
        validated_data["original_filename"] = sanitize_original_filename(file_obj.name)
        validated_data["mime_type"] = getattr(file_obj, "content_type", "")
        validated_data["file_size"] = file_obj.size
        validated_data["checksum"] = compute_checksum(file_obj)
        return super().create(validated_data)


class VerificationRequestSerializer(serializers.ModelSerializer):
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
        # review_notes is intentionally excluded: internal-only, never
        # serialized to the submitting user, only visible via admin views.

    def create(self, validated_data: dict) -> VerificationRequest:
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


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
        # verified_snapshot is intentionally excluded: internal bookkeeping
        # for the material-edit invalidation rule, not user-facing.

    def create(self, validated_data: dict) -> PropertyVerification:
        validated_data["submitted_by"] = self.context["request"].user
        return super().create(validated_data)
