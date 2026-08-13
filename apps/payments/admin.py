from django.contrib import admin

from apps.payments.models import PaymentDispute, PaymentMilestone, PaymentProof, Transaction


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
