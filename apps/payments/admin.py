from django.contrib import admin

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


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["id", "property", "buyer", "owner", "status", "currency", "created_at"]
    list_filter = ["status", "currency"]
    search_fields = ["id", "property__title", "buyer__email", "owner__email"]


@admin.register(PaymentMilestone)
class PaymentMilestoneAdmin(admin.ModelAdmin):
    list_display = ["id", "transaction", "title", "amount", "currency", "status", "due_date"]
    list_filter = ["status", "currency"]
    search_fields = ["id", "title", "transaction__id"]


@admin.register(PaymentProof)
class PaymentProofAdmin(admin.ModelAdmin):
    list_display = ["id", "milestone", "uploaded_by", "amount_claimed", "created_at"]
    search_fields = ["id", "reference", "milestone__id"]


@admin.register(PaymentDispute)
class PaymentDisputeAdmin(admin.ModelAdmin):
    list_display = ["id", "transaction", "milestone", "opened_by", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["id", "transaction__id"]


@admin.register(EscrowProvider)
class EscrowProviderAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "status", "integration_mode", "created_at"]
    list_filter = ["status", "integration_mode"]
    search_fields = ["name", "slug"]


@admin.register(EscrowTransaction)
class EscrowTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "id", "transaction", "provider", "status", "funding_status",
        "release_status", "currency", "expected_amount", "confirmed_funded_amount",
    ]
    list_filter = ["status", "funding_status", "release_status", "provider"]
    search_fields = ["id", "transaction__id", "external_reference"]


@admin.register(EscrowFundingEvent)
class EscrowFundingEventAdmin(admin.ModelAdmin):
    list_display = ["id", "escrow", "event_type", "amount", "currency", "occurred_at"]
    list_filter = ["event_type", "currency", "is_reconciled"]
    search_fields = ["id", "provider_event_id", "provider_reference", "escrow__id"]


@admin.register(EscrowCondition)
class EscrowConditionAdmin(admin.ModelAdmin):
    list_display = ["id", "escrow", "condition_type", "status", "required", "created_at"]
    list_filter = ["condition_type", "status", "required"]
    search_fields = ["id", "escrow__id"]


@admin.register(EscrowRelease)
class EscrowReleaseAdmin(admin.ModelAdmin):
    list_display = ["id", "escrow", "amount", "currency", "status", "requested_by", "created_at"]
    list_filter = ["status", "currency"]
    search_fields = ["id", "escrow__id", "provider_instruction_id", "provider_reference"]


@admin.register(EscrowRefund)
class EscrowRefundAdmin(admin.ModelAdmin):
    list_display = ["id", "escrow", "amount", "currency", "status", "requested_by", "created_at"]
    list_filter = ["status", "currency"]
    search_fields = ["id", "escrow__id", "provider_instruction_id", "provider_reference"]


@admin.register(EscrowSettlement)
class EscrowSettlementAdmin(admin.ModelAdmin):
    list_display = [
        "id", "escrow", "gross_amount", "seller_amount", "platform_fee_amount",
        "currency", "status", "settled_at",
    ]
    list_filter = ["status", "currency"]
    search_fields = ["id", "escrow__id", "provider_settlement_reference"]


@admin.register(EscrowSettlementAllocation)
class EscrowSettlementAllocationAdmin(admin.ModelAdmin):
    list_display = ["id", "settlement", "allocation_type", "recipient_label", "amount"]
    list_filter = ["allocation_type"]
    search_fields = ["id", "settlement__id", "recipient_label"]


@admin.register(ProviderWebhookEvent)
class ProviderWebhookEventAdmin(admin.ModelAdmin):
    list_display = [
        "id", "provider", "provider_event_id", "event_type",
        "signature_status", "processing_status", "received_at",
    ]
    list_filter = ["provider", "signature_status", "processing_status", "event_type"]
    search_fields = ["id", "provider_event_id", "payload_hash"]


@admin.register(EscrowReconciliationRecord)
class EscrowReconciliationRecordAdmin(admin.ModelAdmin):
    list_display = ["id", "escrow", "status", "expected_amount", "provider_amount", "checked_at"]
    list_filter = ["status"]
    search_fields = ["id", "escrow__id"]


@admin.register(FinancingPartner)
class FinancingPartnerAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "status", "partner_type", "integration_mode"]
    list_filter = ["status", "partner_type", "integration_mode"]
    search_fields = ["name", "slug"]


@admin.register(FinancingProduct)
class FinancingProductAdmin(admin.ModelAdmin):
    list_display = ["name", "partner", "product_type", "status", "currency"]
    list_filter = ["status", "product_type", "currency", "partner"]
    search_fields = ["name", "partner__name"]


@admin.register(FinancingDocumentRequirement)
class FinancingDocumentRequirementAdmin(admin.ModelAdmin):
    list_display = ["product", "document_type", "required", "max_size_mb"]
    list_filter = ["document_type", "required"]


@admin.register(FinancingApplication)
class FinancingApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "application_reference", "applicant", "partner", "product", "status",
        "requested_amount", "currency", "created_at",
    ]
    list_filter = ["status", "partner", "product", "currency", "state"]
    search_fields = ["application_reference", "applicant__email", "property__title"]


@admin.register(FinancingConsent)
class FinancingConsentAdmin(admin.ModelAdmin):
    list_display = ["application", "applicant", "scope", "accepted_terms_version", "consented_at"]
    search_fields = ["application__application_reference", "applicant__email"]


@admin.register(FinancingDocument)
class FinancingDocumentAdmin(admin.ModelAdmin):
    list_display = ["application", "document_type", "uploaded_by", "status", "created_at"]
    list_filter = ["document_type", "status"]
    search_fields = ["application__application_reference", "original_filename", "checksum"]


@admin.register(FinancingPartnerSubmission)
class FinancingPartnerSubmissionAdmin(admin.ModelAdmin):
    list_display = ["application", "partner", "submission_reference", "status", "submitted_at"]
    list_filter = ["status", "partner"]
    search_fields = ["application__application_reference", "submission_reference"]


@admin.register(FinancingOffer)
class FinancingOfferAdmin(admin.ModelAdmin):
    list_display = ["application", "partner", "offer_reference", "status", "approved_amount"]
    list_filter = ["status", "partner", "currency"]
    search_fields = ["application__application_reference", "offer_reference"]


@admin.register(FinancingTimelineEvent)
class FinancingTimelineEventAdmin(admin.ModelAdmin):
    list_display = ["application", "event_type", "visibility", "created_at"]
    list_filter = ["event_type", "visibility"]
    search_fields = ["application__application_reference", "message"]
