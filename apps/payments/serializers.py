from __future__ import annotations

from rest_framework import serializers

from apps.payments.models import PaymentDispute, PaymentMilestone, PaymentProof, Transaction


class PaymentProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProof
        fields = [
            "id", "milestone", "uploaded_by", "file", "original_filename",
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


class TransactionCreateSerializer(TransactionSerializer):
    class Meta(TransactionSerializer.Meta):
        read_only_fields = ["id", "status", "milestones", "disputes", "created_at", "updated_at"]


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
