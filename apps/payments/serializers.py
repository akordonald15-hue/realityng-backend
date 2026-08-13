from __future__ import annotations

from rest_framework import serializers

from apps.payments.models import PaymentDispute, PaymentMilestone, PaymentProof, Transaction
from apps.properties.choices import RentalApplicationStatus
from apps.properties.models import Property, RentalApplication


class PaymentProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProof
        fields = [
            "id", "milestone", "uploaded_by", "original_filename",
            "file_size", "checksum", "amount_claimed", "reference", "note",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "milestone", "uploaded_by", "original_filename",
            "file_size", "checksum", "created_at", "updated_at",
        ]


class PaymentMilestoneSerializer(serializers.ModelSerializer):
    proofs = PaymentProofSerializer(many=True, read_only=True)

    class Meta:
        model = PaymentMilestone
        fields = [
            "id", "transaction", "title", "description", "amount", "currency",
            "due_date", "order", "status", "proofs", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "transaction", "status", "proofs", "created_at", "updated_at"]


class PaymentDisputeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentDispute
        fields = [
            "id", "transaction", "milestone", "opened_by", "reason", "status",
            "resolution_note", "resolved_by", "resolved_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "transaction", "opened_by", "status", "resolution_note",
            "resolved_by", "resolved_at", "created_at", "updated_at",
        ]


class TransactionSerializer(serializers.ModelSerializer):
    milestones = PaymentMilestoneSerializer(many=True, read_only=True)
    disputes = PaymentDisputeSerializer(many=True, read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id", "property", "buyer", "owner", "application", "status",
            "currency", "notes", "milestones", "disputes", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "milestones", "disputes", "created_at", "updated_at"]

    def validate(self, attrs):
        buyer = attrs.get("buyer") or getattr(self.instance, "buyer", None)
        owner = attrs.get("owner") or getattr(self.instance, "owner", None)
        if buyer and owner and buyer_id_equals_owner_id(buyer, owner):
            raise serializers.ValidationError("Buyer and owner cannot be the same user.")
        return attrs


def buyer_id_equals_owner_id(buyer, owner) -> bool:
    return buyer.id == owner.id


class TransactionCreateSerializer(serializers.Serializer):
    property_id = serializers.UUIDField()
    application_id = serializers.UUIDField(required=False, allow_null=True)
    currency = serializers.CharField(max_length=3, required=False, default="NGN")
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_property_id(self, value):
        try:
            prop = Property.objects.select_related("owner").get(id=value)
        except Property.DoesNotExist as exc:
            raise serializers.ValidationError("Property is not available.") from exc
        if prop.deleted_at:
            raise serializers.ValidationError("Property is not available.")
        self.context["property"] = prop
        return value

    def validate_application_id(self, value):
        if value is None:
            return value
        try:
            application = RentalApplication.objects.select_related(
                "property",
                "applicant",
                "property_owner",
            ).get(id=value)
        except RentalApplication.DoesNotExist as exc:
            raise serializers.ValidationError("Application is not available.") from exc
        self.context["application"] = application
        return value

    def validate_currency(self, value):
        value = value.upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Currency must be a 3-letter ISO code.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        prop = self.context["property"]
        application = self.context.get("application")

        if application:
            if application.property_id != prop.id:
                raise serializers.ValidationError(
                    {"application_id": "Application must belong to the selected property."}
                )
            if application.status not in {
                RentalApplicationStatus.SUBMITTED,
                RentalApplicationStatus.UNDER_REVIEW,
                RentalApplicationStatus.APPROVED,
            }:
                raise serializers.ValidationError(
                    {"application_id": "Application is not eligible for transaction tracking."}
                )
            buyer = application.applicant
        else:
            buyer = request.user

        if buyer.id == prop.owner_id:
            raise serializers.ValidationError(
                "Buyer and owner cannot be the same user."
            )

        self.context["buyer"] = buyer
        self.context["owner"] = prop.owner
        return attrs


class MilestoneCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMilestone
        fields = ["title", "description", "amount", "currency", "due_date", "order"]


class PaymentProofCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProof
        fields = ["file", "amount_claimed", "reference", "note"]


class DisputeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentDispute
        fields = ["reason", "milestone"]

    def validate_milestone(self, value):
        if value is None:
            return value
        return value


class DisputeResolveSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[("resolved", "resolved"), ("closed", "closed")])
    resolution_note = serializers.CharField(allow_blank=True, required=False, default="")
