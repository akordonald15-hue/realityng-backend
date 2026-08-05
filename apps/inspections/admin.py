from django.contrib import admin

from apps.inspections.models import (
    InspectionAssignment,
    InspectionEvidence,
    InspectionReport,
    InspectionRequest,
    InspectionTimelineEvent,
    InspectorProfile,
    PropertyWalkthrough,
)


@admin.register(InspectionRequest)
class InspectionRequestAdmin(admin.ModelAdmin):
    list_display = ["property", "requester", "inspection_type", "status", "priority", "created_at"]
    list_filter = ["status", "inspection_type", "priority", "created_at"]
    search_fields = ["property__title", "requester__email", "purpose"]
    readonly_fields = ["created_at", "updated_at", "deleted_at"]


@admin.register(InspectorProfile)
class InspectorProfileAdmin(admin.ModelAdmin):
    list_display = ["display_name", "user", "verification_status", "availability_status", "active"]
    list_filter = ["verification_status", "availability_status", "active"]
    search_fields = ["display_name", "user__email", "professional_title"]


@admin.register(InspectionAssignment)
class InspectionAssignmentAdmin(admin.ModelAdmin):
    list_display = ["inspection_request", "inspector", "status", "assigned_at"]
    list_filter = ["status", "assigned_at"]
    search_fields = ["inspection_request__property__title", "inspector__email"]


@admin.register(PropertyWalkthrough)
class PropertyWalkthroughAdmin(admin.ModelAdmin):
    list_display = ["title", "property", "uploaded_by", "status", "is_featured", "created_at"]
    list_filter = ["status", "is_featured", "created_at"]
    search_fields = ["title", "property__title", "uploaded_by__email"]


@admin.register(InspectionReport)
class InspectionReportAdmin(admin.ModelAdmin):
    list_display = ["inspection_request", "inspector", "status", "risk_level", "created_at"]
    list_filter = ["status", "risk_level", "overall_condition", "created_at"]
    search_fields = ["inspection_request__property__title", "inspector__email", "summary"]


@admin.register(InspectionEvidence)
class InspectionEvidenceAdmin(admin.ModelAdmin):
    list_display = ["inspection_report", "evidence_type", "category", "visibility", "uploaded_by"]
    list_filter = ["evidence_type", "category", "visibility", "created_at"]
    search_fields = ["inspection_report__inspection_request__property__title", "caption"]


@admin.register(InspectionTimelineEvent)
class InspectionTimelineEventAdmin(admin.ModelAdmin):
    list_display = ["inspection_request", "event_type", "actor", "is_internal", "created_at"]
    list_filter = ["event_type", "is_internal", "created_at"]
    search_fields = ["inspection_request__property__title", "description"]
