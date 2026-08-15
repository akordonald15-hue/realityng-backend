from __future__ import annotations

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.payments.choices import (
    FinancingApplicationStatus,
    FinancingDocumentType,
    FinancingProductStatus,
    FinancingTimelineVisibility,
)
from apps.payments.models import (
    EscrowCondition,
    EscrowFundingEvent,
    EscrowProvider,
    EscrowReconciliationRecord,
    EscrowRefund,
    EscrowRelease,
    EscrowSettlement,
    EscrowSettlementAllocation,
    EscrowTransaction,
    FinancingApplication,
    FinancingConsent,
    FinancingDocument,
    FinancingDocumentRequirement,
    FinancingOffer,
    FinancingPartner,
    FinancingPartnerSubmission,
    FinancingProduct,
    FinancingTimelineEvent,
    PaymentDispute,
    PaymentMilestone,
    PaymentProof,
    ProviderWebhookEvent,
    Transaction,
)
from apps.payments.validators import compute_checksum, sanitize_original_filename
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


class EscrowProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscrowProvider
        fields = [
            "id", "name", "slug", "status", "integration_mode",
            "supports_partial_funding", "supports_partial_release", "supports_refunds",
            "supports_webhooks", "supports_reconciliation", "supported_currencies",
            "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EscrowFundingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscrowFundingEvent
        fields = [
            "id", "escrow", "provider_event_id", "provider_reference", "amount",
            "currency", "event_type", "provider_status", "occurred_at",
            "recorded_by", "raw_reference", "is_reconciled", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "escrow", "recorded_by", "created_at", "updated_at"]


class EscrowConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscrowCondition
        fields = [
            "id", "escrow", "condition_type", "status", "description", "required",
            "inspection_request", "construction_milestone", "satisfied_at",
            "satisfied_by", "failed_at", "failure_reason", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "escrow", "status", "satisfied_at", "satisfied_by",
            "failed_at", "failure_reason", "created_at", "updated_at",
        ]


class EscrowReleaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscrowRelease
        fields = [
            "id", "escrow", "amount", "currency", "status", "requested_by",
            "approved_by", "provider_instruction_id", "provider_reference",
            "idempotency_key", "reason", "approved_at", "instructed_at",
            "confirmed_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "escrow", "status", "requested_by", "approved_by",
            "provider_instruction_id", "provider_reference", "approved_at",
            "instructed_at", "confirmed_at", "created_at", "updated_at",
        ]


class EscrowRefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscrowRefund
        fields = [
            "id", "escrow", "amount", "currency", "status", "requested_by",
            "approved_by", "provider_instruction_id", "provider_reference",
            "idempotency_key", "reason", "approved_at", "instructed_at",
            "confirmed_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "escrow", "status", "requested_by", "approved_by",
            "provider_instruction_id", "provider_reference", "approved_at",
            "instructed_at", "confirmed_at", "created_at", "updated_at",
        ]


class EscrowSettlementAllocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscrowSettlementAllocation
        fields = [
            "id", "allocation_type", "recipient_label", "amount", "currency",
            "provider_reference", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EscrowSettlementSerializer(serializers.ModelSerializer):
    allocations = EscrowSettlementAllocationSerializer(many=True, read_only=True)

    class Meta:
        model = EscrowSettlement
        fields = [
            "id", "escrow", "provider_settlement_reference", "gross_amount",
            "seller_amount", "platform_fee_amount", "provider_fee_amount",
            "currency", "status", "settled_at", "recorded_by", "allocations",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "escrow", "recorded_by", "allocations", "created_at", "updated_at",
        ]


class EscrowReconciliationRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscrowReconciliationRecord
        fields = [
            "id", "escrow", "status", "expected_amount", "provider_amount",
            "expected_status", "provider_status", "mismatch_details", "checked_at",
            "resolved_at", "resolved_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "escrow", "resolved_at", "resolved_by", "created_at", "updated_at",
        ]


class ProviderWebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProviderWebhookEvent
        fields = [
            "id", "provider", "related_escrow", "provider_event_id", "event_type",
            "signature_status", "payload_hash", "processing_status", "received_at",
            "processed_at", "attempt_count", "last_error", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EscrowTransactionSerializer(serializers.ModelSerializer):
    provider = EscrowProviderSerializer(read_only=True)
    funding_events = EscrowFundingEventSerializer(many=True, read_only=True)
    conditions = EscrowConditionSerializer(many=True, read_only=True)
    releases = EscrowReleaseSerializer(many=True, read_only=True)
    refunds = EscrowRefundSerializer(many=True, read_only=True)
    settlements = EscrowSettlementSerializer(many=True, read_only=True)
    reconciliation_records = EscrowReconciliationRecordSerializer(many=True, read_only=True)

    class Meta:
        model = EscrowTransaction
        fields = [
            "id", "transaction", "provider", "external_reference", "currency",
            "expected_amount", "confirmed_funded_amount", "status", "funding_status",
            "release_status", "refund_status", "reconciliation_status",
            "platform_fee_type", "platform_fee_value", "expected_platform_fee",
            "provider_fee", "fee_status", "created_by", "funded_at", "released_at",
            "refunded_at", "closed_at", "funding_events", "conditions", "releases",
            "refunds", "settlements", "reconciliation_records", "created_at", "updated_at",
        ]
        read_only_fields = fields


class EscrowCreateSerializer(serializers.Serializer):
    provider_id = serializers.UUIDField()
    expected_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField(max_length=3, required=False)
    external_reference = serializers.CharField(required=False, allow_blank=True, default="")
    platform_fee_type = serializers.ChoiceField(
        choices=["none", "percentage", "fixed", "hybrid"],
        required=False,
        default="none",
    )
    platform_fee_value = serializers.DecimalField(
        max_digits=12,
        decimal_places=4,
        required=False,
        default=0,
    )
    provider_fee = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        default=0,
    )
    idempotency_key = serializers.CharField(required=False, allow_blank=True, default="")


class RecordProviderReferenceSerializer(serializers.Serializer):
    external_reference = serializers.CharField(max_length=160)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class RecordFundingSerializer(serializers.Serializer):
    provider_event_id = serializers.CharField(max_length=180)
    provider_reference = serializers.CharField(required=False, allow_blank=True, default="")
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField(max_length=3)
    event_type = serializers.ChoiceField(
        choices=[
            "funding_confirmed",
            "partial_funding_confirmed",
            "funding_reversed",
            "overpayment",
            "underpayment",
        ],
        required=False,
        default="funding_confirmed",
    )
    provider_status = serializers.CharField(required=False, allow_blank=True, default="")
    raw_reference = serializers.CharField(required=False, allow_blank=True, default="")


class EscrowConditionCreateSerializer(serializers.Serializer):
    condition_type = serializers.ChoiceField(
        choices=[
            "property_verified",
            "inspection_passed",
            "title_verified",
            "buyer_confirmation",
            "seller_documents_complete",
            "construction_milestone_approved",
            "manual_condition",
        ]
    )
    description = serializers.CharField(required=False, allow_blank=True, default="")
    required = serializers.BooleanField(required=False, default=True)
    inspection_request = serializers.UUIDField(required=False, allow_null=True)
    construction_milestone = serializers.UUIDField(required=False, allow_null=True)


class EscrowConditionSatisfySerializer(serializers.Serializer):
    condition_id = serializers.UUIDField()
    note = serializers.CharField(required=False, allow_blank=True, default="")


class EscrowReleaseRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    idempotency_key = serializers.CharField(required=False, allow_blank=True, default="")


class EscrowReleaseApproveSerializer(serializers.Serializer):
    release_id = serializers.UUIDField()
    provider_instruction_id = serializers.CharField(required=False, allow_blank=True, default="")
    note = serializers.CharField(required=False, allow_blank=True, default="")


class EscrowReleaseConfirmSerializer(serializers.Serializer):
    release_id = serializers.UUIDField()
    provider_reference = serializers.CharField(max_length=180)


class EscrowRefundRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)
    reason = serializers.CharField()
    idempotency_key = serializers.CharField(required=False, allow_blank=True, default="")


class EscrowRefundApproveSerializer(serializers.Serializer):
    refund_id = serializers.UUIDField()
    provider_instruction_id = serializers.CharField(required=False, allow_blank=True, default="")
    note = serializers.CharField(required=False, allow_blank=True, default="")


class EscrowRefundConfirmSerializer(serializers.Serializer):
    refund_id = serializers.UUIDField()
    provider_reference = serializers.CharField(max_length=180)


class EscrowSettlementRecordSerializer(serializers.Serializer):
    provider_settlement_reference = serializers.CharField(max_length=180)
    gross_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    seller_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    platform_fee_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        default=0,
    )
    provider_fee_amount = serializers.DecimalField(
        max_digits=18,
        decimal_places=2,
        required=False,
        default=0,
    )
    allocations = EscrowSettlementAllocationSerializer(many=True, required=False)


class EscrowReconcileSerializer(serializers.Serializer):
    provider_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    provider_status = serializers.CharField(max_length=40)
    mismatch_details = serializers.CharField(required=False, allow_blank=True, default="")


class FinancingPartnerPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancingPartner
        fields = [
            "id", "name", "slug", "status", "partner_type", "integration_mode",
            "supported_products", "supported_states", "minimum_amount",
            "maximum_amount", "contact_policy", "created_at", "updated_at",
        ]
        read_only_fields = fields


class FinancingDocumentRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancingDocumentRequirement
        fields = [
            "id", "document_type", "required", "description", "allowed_mime_types",
            "max_size_mb", "created_at", "updated_at",
        ]
        read_only_fields = fields


class FinancingProductSerializer(serializers.ModelSerializer):
    partner = FinancingPartnerPublicSerializer(read_only=True)
    document_requirements = FinancingDocumentRequirementSerializer(many=True, read_only=True)

    class Meta:
        model = FinancingProduct
        fields = [
            "id", "partner", "name", "product_type", "status", "currency",
            "minimum_amount", "maximum_amount", "minimum_tenor_months",
            "maximum_tenor_months", "requires_property", "requires_income_documents",
            "requires_identity_verification", "requires_bank_statement", "description",
            "document_requirements", "created_at", "updated_at",
        ]
        read_only_fields = fields


class FinancingDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancingDocument
        fields = [
            "id", "application", "uploaded_by", "document_type", "original_filename",
            "mime_type", "file_size", "checksum", "status", "reviewed_by",
            "reviewed_at", "rejection_reason", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "application", "uploaded_by", "original_filename", "mime_type",
            "file_size", "checksum", "status", "reviewed_by", "reviewed_at",
            "rejection_reason", "created_at", "updated_at",
        ]


class FinancingDocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancingDocument
        fields = ["document_type", "file"]

    def validate_document_type(self, value):
        if value not in {choice.value for choice in FinancingDocumentType}:
            raise serializers.ValidationError("Unsupported document type.")
        return value

    def create(self, validated_data):
        file = validated_data["file"]
        return FinancingDocument.objects.create(
            application=self.context["application"],
            uploaded_by=self.context["request"].user,
            document_type=validated_data["document_type"],
            file=file,
            original_filename=sanitize_original_filename(file.name),
            mime_type=getattr(file, "content_type", ""),
            file_size=file.size,
            checksum=compute_checksum(file),
        )


class FinancingConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancingConsent
        fields = [
            "id", "application", "applicant", "scope", "accepted_terms_version",
            "consented_at", "revoked_at", "ip_address", "user_agent",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class FinancingTimelineEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancingTimelineEvent
        fields = [
            "id", "application", "actor", "event_type", "message", "visibility",
            "metadata", "created_at", "updated_at",
        ]
        read_only_fields = fields


class FinancingPartnerSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancingPartnerSubmission
        fields = [
            "id", "application", "partner", "submission_reference", "status",
            "submitted_at", "response_received_at", "payload_hash", "error_message",
            "retry_count", "created_at", "updated_at",
        ]
        read_only_fields = fields


class FinancingOfferSerializer(serializers.ModelSerializer):
    partner = FinancingPartnerPublicSerializer(read_only=True)

    class Meta:
        model = FinancingOffer
        fields = [
            "id", "application", "partner", "offer_reference", "status",
            "approved_amount", "currency", "tenor_months", "interest_rate_display",
            "fees_display", "monthly_payment_display", "partner_terms_summary",
            "expires_at", "accepted_at", "declined_at", "created_at", "updated_at",
        ]
        read_only_fields = fields


class FinancingApplicationSerializer(serializers.ModelSerializer):
    product = FinancingProductSerializer(read_only=True)
    partner = FinancingPartnerPublicSerializer(read_only=True)
    documents = FinancingDocumentSerializer(many=True, read_only=True)
    offers = FinancingOfferSerializer(many=True, read_only=True)
    timeline_events = serializers.SerializerMethodField()

    class Meta:
        model = FinancingApplication
        fields = [
            "id", "applicant", "property", "transaction", "product", "partner",
            "application_reference", "status", "requested_amount", "currency",
            "purpose", "preferred_tenor_months", "employment_status",
            "monthly_income_band", "state", "city", "consent_status",
            "applicant_message", "partner_status", "partner_reference",
            "submitted_at", "partner_submitted_at", "decision_at", "documents",
            "offers", "timeline_events", "created_at", "updated_at",
        ]
        read_only_fields = fields

    @extend_schema_field(FinancingTimelineEventSerializer(many=True))
    def get_timeline_events(self, obj):
        request = self.context.get("request")
        is_admin = bool(request and getattr(request.user, "is_staff", False))
        events = obj.timeline_events.all()
        if not is_admin:
            events = events.exclude(visibility=FinancingTimelineVisibility.INTERNAL)
        return FinancingTimelineEventSerializer(events, many=True).data


class FinancingApplicationAdminSerializer(FinancingApplicationSerializer):
    partner_submissions = FinancingPartnerSubmissionSerializer(many=True, read_only=True)

    class Meta(FinancingApplicationSerializer.Meta):
        fields = FinancingApplicationSerializer.Meta.fields + [
            "admin_notes",
            "partner_submissions",
        ]
        read_only_fields = fields


class FinancingApplicationCreateSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    property_id = serializers.UUIDField(required=False, allow_null=True)
    transaction_id = serializers.UUIDField(required=False, allow_null=True)
    requested_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField(max_length=3, required=False, default="NGN")
    purpose = serializers.CharField()
    preferred_tenor_months = serializers.IntegerField(min_value=1)
    employment_status = serializers.CharField(max_length=80)
    monthly_income_band = serializers.CharField(max_length=80)
    state = serializers.CharField(max_length=100)
    city = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    applicant_message = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_product_id(self, value):
        try:
            product = FinancingProduct.objects.select_related("partner").get(
                id=value,
                status=FinancingProductStatus.ACTIVE,
                partner__status="active",
            )
        except FinancingProduct.DoesNotExist as exc:
            raise serializers.ValidationError("Financing product is not available.") from exc
        self.context["product"] = product
        return value

    def validate_property_id(self, value):
        if value is None:
            return value
        try:
            prop = Property.objects.get(id=value)
        except Property.DoesNotExist as exc:
            raise serializers.ValidationError("Property is not available.") from exc
        self.context["property"] = prop
        return value

    def validate_transaction_id(self, value):
        if value is None:
            return value
        try:
            transaction = Transaction.objects.select_related("property").get(id=value)
        except Transaction.DoesNotExist as exc:
            raise serializers.ValidationError("Transaction is not available.") from exc
        request = self.context["request"]
        if transaction.buyer_id != request.user.id:
            raise serializers.ValidationError("Transaction is not available.")
        self.context["transaction"] = transaction
        return value

    def validate_currency(self, value):
        value = value.upper()
        if len(value) != 3 or not value.isalpha():
            raise serializers.ValidationError("Currency must be a 3-letter ISO code.")
        return value

    def validate(self, attrs):
        product = self.context["product"]
        amount = attrs["requested_amount"]
        tenor = attrs["preferred_tenor_months"]
        state = attrs["state"]
        if attrs["currency"].upper() != product.currency:
            raise serializers.ValidationError({"currency": "Currency must match the product."})
        if amount < product.minimum_amount or amount > product.maximum_amount:
            raise serializers.ValidationError(
                {"requested_amount": "Amount is outside the selected product limits."}
            )
        if tenor < product.minimum_tenor_months or tenor > product.maximum_tenor_months:
            raise serializers.ValidationError(
                {"preferred_tenor_months": "Tenor is outside the selected product limits."}
            )
        if product.requires_property and not (
            self.context.get("property") or self.context.get("transaction")
        ):
            raise serializers.ValidationError(
                {"property_id": "This product requires a property or transaction."}
            )
        if not product.partner.supports_product_type(product.product_type):
            raise serializers.ValidationError("Partner does not support this product.")
        if not product.partner.supports_state(state):
            raise serializers.ValidationError({"state": "Partner does not support this state."})
        transaction = self.context.get("transaction")
        prop = self.context.get("property")
        if transaction and prop and transaction.property_id != prop.id:
            raise serializers.ValidationError(
                {"transaction_id": "Transaction must belong to the selected property."}
            )
        return attrs


class FinancingApplicationUpdateSerializer(serializers.Serializer):
    requested_amount = serializers.DecimalField(max_digits=18, decimal_places=2, required=False)
    purpose = serializers.CharField(required=False)
    preferred_tenor_months = serializers.IntegerField(min_value=1, required=False)
    employment_status = serializers.CharField(max_length=80, required=False)
    monthly_income_band = serializers.CharField(max_length=80, required=False)
    state = serializers.CharField(max_length=100, required=False)
    city = serializers.CharField(max_length=120, required=False, allow_blank=True)
    applicant_message = serializers.CharField(required=False, allow_blank=True)


class FinancingConsentCreateSerializer(serializers.Serializer):
    scope = serializers.CharField(max_length=200, default="financing_partner_submission")
    accepted_terms_version = serializers.CharField(max_length=40, required=False)


class FinancingApplicationSubmitSerializer(serializers.Serializer):
    pass


class FinancingAdminDecisionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            FinancingApplicationStatus.UNDER_REVIEW,
            FinancingApplicationStatus.MORE_INFORMATION_REQUESTED,
            FinancingApplicationStatus.REJECTED,
            FinancingApplicationStatus.CANCELLED,
        ]
    )
    message = serializers.CharField(required=False, allow_blank=True, default="")
    admin_notes = serializers.CharField(required=False, allow_blank=True, default="")


class FinancingPartnerSubmitSerializer(serializers.Serializer):
    submission_reference = serializers.CharField(max_length=160)
    payload_hash = serializers.CharField(
        max_length=64,
        required=False,
        allow_blank=True,
        default="",
    )
    message = serializers.CharField(required=False, allow_blank=True, default="")


class FinancingOfferCreateSerializer(serializers.Serializer):
    offer_reference = serializers.CharField(max_length=160)
    approved_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    currency = serializers.CharField(max_length=3)
    tenor_months = serializers.IntegerField(min_value=1)
    interest_rate_display = serializers.CharField(required=False, allow_blank=True, default="")
    fees_display = serializers.CharField(required=False, allow_blank=True, default="")
    monthly_payment_display = serializers.CharField(required=False, allow_blank=True, default="")
    partner_terms_summary = serializers.CharField(required=False, allow_blank=True, default="")
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
