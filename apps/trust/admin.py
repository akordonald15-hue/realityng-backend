"""Django admin configuration for the trust and verification app."""

from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from apps.trust.models import PropertyVerification, VerificationDocument, VerificationRequest


class VerificationDocumentInline(admin.TabularInline):
    model = VerificationDocument
    extra = 0
    fields = (
        "document_type",
        "original_filename",
        "mime_type",
        "file_size",
        "reviewed_status",
        "uploaded_at",
    )
    readonly_fields = ("original_filename", "mime_type", "file_size", "uploaded_at")
    can_delete = False
    show_change_link = True


@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "verification_type",
        "status_badge",
        "reviewer",
        "submitted_at",
        "expiry_date",
    )
    list_filter = ("verification_type", "status")
    search_fields = (
        "user__email",
        "business_name",
        "cac_registration_number",
        "phone_number",
    )
    autocomplete_fields = ("user", "reviewer")
    readonly_fields = ("id", "created_at", "updated_at", "submitted_at", "reviewed_at")
    inlines = (VerificationDocumentInline,)
    ordering = ("-created_at",)

    fieldsets = (
        ("Submission", {
            "fields": (
                "id",
                "user",
                "verification_type",
                "status",
            ),
        }),
        ("Submitted Details", {
            "fields": (
                "business_name",
                "cac_registration_number",
                "trade_category",
                "years_experience",
                "phone_number",
                "contact_address",
                "city",
            ),
        }),
        ("Review", {
            "fields": (
                "reviewer",
                "reviewed_at",
                "rejection_reason",
                "review_notes",
                "expiry_date",
            ),
        }),
        ("Timestamps", {
            "fields": ("submitted_at", "created_at", "updated_at"),
        }),
    )

    @admin.display(description="Status")
    def status_badge(self, obj: VerificationRequest) -> str:
        colors = {
            "not_submitted": "#9CA3AF",
            "pending": "#F59E0B",
            "under_review": "#3B82F6",
            "approved": "#10B981",
            "rejected": "#EF4444",
            "needs_more_information": "#F59E0B",
            "expired": "#6B7280",
            "suspended": "#DC2626",
        }
        color = colors.get(obj.status, "#9CA3AF")
        return format_html(
            '<span style="color: {}; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display(),
        )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user", "reviewer")


@admin.register(PropertyVerification)
class PropertyVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "property",
        "submitted_by",
        "status_badge",
        "reviewer",
        "submitted_at",
        "expiry_date",
    )
    list_filter = ("status",)
    search_fields = ("property__title", "property__slug", "submitted_by__email")
    autocomplete_fields = ("property", "submitted_by", "reviewer")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "submitted_at",
        "reviewed_at",
        "verified_snapshot",
    )
    ordering = ("-created_at",)

    fieldsets = (
        ("Submission", {
            "fields": ("id", "property", "submitted_by", "status"),
        }),
        ("Evidence", {
            "fields": ("ownership_evidence", "location_evidence", "inspection_evidence"),
        }),
        ("Review", {
            "fields": ("reviewer", "reviewed_at", "rejection_reason", "expiry_date"),
        }),
        ("Snapshot", {
            "fields": ("verified_snapshot",),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("submitted_at", "created_at", "updated_at"),
        }),
    )

    @admin.display(description="Status")
    def status_badge(self, obj: PropertyVerification) -> str:
        colors = {
            "not_submitted": "#9CA3AF",
            "pending": "#F59E0B",
            "under_review": "#3B82F6",
            "approved": "#10B981",
            "rejected": "#EF4444",
            "needs_more_information": "#F59E0B",
            "expired": "#6B7280",
            "suspended": "#DC2626",
        }
        color = colors.get(obj.status, "#9CA3AF")
        return format_html(
            '<span style="color: {}; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display(),
        )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("property", "submitted_by", "reviewer")
