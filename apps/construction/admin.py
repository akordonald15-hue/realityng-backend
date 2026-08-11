from django.contrib import admin

from apps.construction.models import (
    ConstructionEvidence,
    ConstructionMilestone,
    ConstructionMilestoneInspection,
    ConstructionProgressUpdate,
    ConstructionProject,
    ConstructionTimelineEvent,
    ProjectStakeholder,
)


class ConstructionMilestoneInline(admin.TabularInline):
    model = ConstructionMilestone
    extra = 0
    fields = ["name", "sequence", "weight", "status", "progress_percent", "requires_inspection"]
    readonly_fields = ["progress_percent"]


class ProjectStakeholderInline(admin.TabularInline):
    model = ProjectStakeholder
    extra = 0
    fields = ["user", "stakeholder_role", "access_level", "status", "invited_by"]


@admin.register(ConstructionProject)
class ConstructionProjectAdmin(admin.ModelAdmin):
    inlines = [ConstructionMilestoneInline, ProjectStakeholderInline]
    list_display = ["name", "property", "status", "overall_progress", "owner", "project_manager"]
    list_filter = ["status", "project_type", "visibility", "created_at"]
    search_fields = ["name", "property__title", "owner__email", "project_manager__email"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at", "deleted_at", "overall_progress"]


@admin.register(ProjectStakeholder)
class ProjectStakeholderAdmin(admin.ModelAdmin):
    list_display = ["project", "user", "stakeholder_role", "access_level", "status"]
    list_filter = ["stakeholder_role", "access_level", "status"]
    search_fields = ["project__name", "user__email", "notes"]


@admin.register(ConstructionMilestone)
class ConstructionMilestoneAdmin(admin.ModelAdmin):
    list_display = [
        "project",
        "sequence",
        "name",
        "status",
        "progress_percent",
        "requires_inspection",
    ]
    list_filter = ["status", "requires_inspection", "blocking"]
    search_fields = ["project__name", "name", "description"]


@admin.register(ConstructionProgressUpdate)
class ConstructionProgressUpdateAdmin(admin.ModelAdmin):
    list_display = ["project", "milestone", "title", "status", "current_progress", "submitted_by"]
    list_filter = ["status", "created_at"]
    search_fields = ["project__name", "milestone__name", "title", "summary"]


@admin.register(ConstructionEvidence)
class ConstructionEvidenceAdmin(admin.ModelAdmin):
    list_display = ["project", "milestone", "evidence_type", "visibility", "status", "uploaded_by"]
    list_filter = ["evidence_type", "visibility", "status", "created_at"]
    search_fields = ["project__name", "caption", "uploaded_by__email"]


@admin.register(ConstructionMilestoneInspection)
class ConstructionMilestoneInspectionAdmin(admin.ModelAdmin):
    list_display = ["milestone", "inspection_request", "requested_by", "created_at"]
    search_fields = ["milestone__name", "inspection_request__purpose", "requested_by__email"]


@admin.register(ConstructionTimelineEvent)
class ConstructionTimelineEventAdmin(admin.ModelAdmin):
    list_display = ["project", "milestone", "event_type", "actor", "is_internal", "created_at"]
    list_filter = ["event_type", "is_internal", "created_at"]
    search_fields = ["project__name", "event_type", "description", "actor__email"]
