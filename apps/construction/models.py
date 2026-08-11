from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from apps.common.models import BaseModel
from apps.construction.choices import (
    ConstructionEvidenceStatus,
    ConstructionEvidenceType,
    ConstructionEvidenceVisibility,
    ConstructionMilestoneStatus,
    ConstructionProgressUpdateStatus,
    ConstructionProjectStatus,
    ConstructionProjectType,
    ConstructionProjectVisibility,
    ProjectAccessLevel,
    ProjectStakeholderRole,
    ProjectStakeholderStatus,
)
from apps.construction.storage import get_construction_evidence_storage
from apps.inspections.models import InspectionRequest
from apps.properties.models import Property


def construction_evidence_upload_to(instance: ConstructionEvidence, filename: str) -> str:
    return f"construction/{instance.project_id}/evidence/{filename}"


class ConstructionProject(BaseModel):
    VALID_STATUS_TRANSITIONS = {
        ConstructionProjectStatus.DRAFT: {
            ConstructionProjectStatus.PLANNED,
            ConstructionProjectStatus.CANCELLED,
        },
        ConstructionProjectStatus.PLANNED: {
            ConstructionProjectStatus.ACTIVE,
            ConstructionProjectStatus.CANCELLED,
            ConstructionProjectStatus.ON_HOLD,
        },
        ConstructionProjectStatus.ACTIVE: {
            ConstructionProjectStatus.PAUSED,
            ConstructionProjectStatus.ON_HOLD,
            ConstructionProjectStatus.COMPLETED,
            ConstructionProjectStatus.CANCELLED,
        },
        ConstructionProjectStatus.PAUSED: {
            ConstructionProjectStatus.ACTIVE,
            ConstructionProjectStatus.CANCELLED,
        },
        ConstructionProjectStatus.ON_HOLD: {
            ConstructionProjectStatus.ACTIVE,
            ConstructionProjectStatus.CANCELLED,
        },
        ConstructionProjectStatus.COMPLETED: {ConstructionProjectStatus.ARCHIVED},
        ConstructionProjectStatus.CANCELLED: {ConstructionProjectStatus.ARCHIVED},
        ConstructionProjectStatus.ARCHIVED: set(),
    }

    property = models.ForeignKey(
        Property,
        on_delete=models.PROTECT,
        related_name="construction_projects",
    )
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField(blank=True)
    project_type = models.CharField(
        max_length=40,
        choices=ConstructionProjectType.choices,
        default=ConstructionProjectType.RENOVATION,
    )
    status = models.CharField(
        max_length=20,
        choices=ConstructionProjectStatus.choices,
        default=ConstructionProjectStatus.DRAFT,
        db_index=True,
    )
    visibility = models.CharField(
        max_length=24,
        choices=ConstructionProjectVisibility.choices,
        default=ConstructionProjectVisibility.STAKEHOLDERS,
    )
    planned_start_date = models.DateField(null=True, blank=True)
    planned_end_date = models.DateField(null=True, blank=True)
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    overall_progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_construction_projects",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_construction_projects",
    )
    project_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_construction_projects",
    )
    contractor_name_or_reference = models.CharField(max_length=180, blank=True)
    estimated_duration_days = models.PositiveIntegerField(null=True, blank=True)
    current_milestone = models.ForeignKey(
        "ConstructionMilestone",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property", "status"]),
            models.Index(fields=["owner", "status", "created_at"]),
            models.Index(fields=["project_manager", "status"]),
            models.Index(fields=["status", "planned_end_date"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self) -> str:
        base_slug = slugify(f"{self.property_id}-{self.name}")[:190] or "construction-project"
        candidate = base_slug
        counter = 2
        queryset = ConstructionProject.all_objects.all()
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)
        while queryset.filter(slug=candidate).exists():
            suffix = f"-{counter}"
            candidate = f"{base_slug[: 220 - len(suffix)]}{suffix}"
            counter += 1
        return candidate

    def can_transition_to(self, next_status: str) -> bool:
        return next_status in self.VALID_STATUS_TRANSITIONS.get(self.status, set())

    def transition_to(self, next_status: str) -> None:
        if next_status == self.status:
            return
        if not self.can_transition_to(next_status):
            raise ValueError(f"Project cannot move from {self.status} to {next_status}.")
        self.status = next_status
        update_fields = ["status", "updated_at"]
        today = timezone.localdate()
        now = timezone.now()
        if next_status == ConstructionProjectStatus.ACTIVE and not self.actual_start_date:
            self.actual_start_date = today
            update_fields.append("actual_start_date")
        elif next_status == ConstructionProjectStatus.COMPLETED:
            self.actual_end_date = today
            self.overall_progress = Decimal("100.00")
            update_fields += ["actual_end_date", "overall_progress"]
        elif next_status == ConstructionProjectStatus.ARCHIVED:
            self.archived_at = now
            update_fields.append("archived_at")
        self.save(update_fields=update_fields)


class ProjectStakeholder(BaseModel):
    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="stakeholders",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="construction_stakeholderships",
    )
    stakeholder_role = models.CharField(
        max_length=24,
        choices=ProjectStakeholderRole.choices,
        default=ProjectStakeholderRole.VIEWER,
    )
    access_level = models.CharField(
        max_length=16,
        choices=ProjectAccessLevel.choices,
        default=ProjectAccessLevel.READ_ONLY,
    )
    status = models.CharField(
        max_length=16,
        choices=ProjectStakeholderStatus.choices,
        default=ProjectStakeholderStatus.INVITED,
        db_index=True,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invited_construction_stakeholders",
    )
    invited_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["stakeholder_role", "user__email"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["stakeholder_role", "access_level"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                condition=Q(deleted_at__isnull=True),
                name="unique_live_project_stakeholder_per_user",
            ),
        ]

    def accept(self) -> None:
        self.status = ProjectStakeholderStatus.ACTIVE
        self.accepted_at = timezone.now()
        self.save(update_fields=["status", "accepted_at", "updated_at"])

    def revoke(self) -> None:
        self.status = ProjectStakeholderStatus.REVOKED
        self.revoked_at = timezone.now()
        self.save(update_fields=["status", "revoked_at", "updated_at"])


class ConstructionMilestone(BaseModel):
    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="milestones",
    )
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    sequence = models.PositiveSmallIntegerField(default=1)
    weight = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    status = models.CharField(
        max_length=24,
        choices=ConstructionMilestoneStatus.choices,
        default=ConstructionMilestoneStatus.NOT_STARTED,
        db_index=True,
    )
    planned_start_date = models.DateField(null=True, blank=True)
    planned_end_date = models.DateField(null=True, blank=True)
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    progress_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    requires_inspection = models.BooleanField(default=False)
    blocking = models.BooleanField(default=False)
    depends_on = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dependent_milestones",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["sequence", "created_at"]
        indexes = [
            models.Index(fields=["project", "sequence"]),
            models.Index(fields=["project", "status"]),
            models.Index(fields=["requires_inspection", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "sequence"],
                condition=Q(deleted_at__isnull=True),
                name="unique_live_construction_milestone_sequence",
            ),
            models.CheckConstraint(
                condition=Q(weight__gt=0),
                name="construction_milestone_weight_positive",
            ),
            models.CheckConstraint(
                condition=Q(progress_percent__gte=0, progress_percent__lte=100),
                name="construction_milestone_progress_between_0_and_100",
            ),
        ]

    def clean(self) -> None:
        if self.depends_on_id and self.depends_on_id == self.id:
            raise ValidationError({"depends_on": "A milestone cannot depend on itself."})

    def mark_completed_if_allowed(self) -> None:
        if (
            self.requires_inspection
            and not self.inspection_links.filter(inspection_request__status="completed").exists()
        ):
            self.status = ConstructionMilestoneStatus.AWAITING_INSPECTION
        else:
            self.status = ConstructionMilestoneStatus.COMPLETED
            self.actual_end_date = timezone.localdate()
        self.progress_percent = Decimal("100.00")
        self.save(update_fields=["status", "actual_end_date", "progress_percent", "updated_at"])


class ConstructionProgressUpdate(BaseModel):
    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="progress_updates",
    )
    milestone = models.ForeignKey(
        ConstructionMilestone,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="progress_updates",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="construction_progress_updates",
    )
    title = models.CharField(max_length=180)
    summary = models.TextField()
    work_completed = models.TextField(blank=True)
    current_progress = models.DecimalField(max_digits=5, decimal_places=2)
    issues = models.TextField(blank=True)
    blockers = models.TextField(blank=True)
    next_steps = models.TextField(blank=True)
    reporting_period_start = models.DateField(null=True, blank=True)
    reporting_period_end = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=24,
        choices=ConstructionProgressUpdateStatus.choices,
        default=ConstructionProgressUpdateStatus.DRAFT,
        db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_construction_progress_updates",
    )
    rejection_reason = models.TextField(blank=True)
    correction_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "status", "created_at"]),
            models.Index(fields=["milestone", "status", "created_at"]),
            models.Index(fields=["submitted_by", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(current_progress__gte=0, current_progress__lte=100),
                name="construction_update_progress_between_0_and_100",
            ),
        ]

    def submit(self) -> None:
        self.status = ConstructionProgressUpdateStatus.SUBMITTED
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "submitted_at", "updated_at"])

    def approve(self, *, reviewer) -> None:
        self.status = ConstructionProgressUpdateStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])


class ConstructionEvidence(BaseModel):
    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    milestone = models.ForeignKey(
        ConstructionMilestone,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="evidence",
    )
    progress_update = models.ForeignKey(
        ConstructionProgressUpdate,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="evidence",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="construction_evidence_uploads",
    )
    evidence_type = models.CharField(
        max_length=16,
        choices=ConstructionEvidenceType.choices,
        default=ConstructionEvidenceType.PHOTO,
    )
    file = models.FileField(
        upload_to=construction_evidence_upload_to,
        storage=get_construction_evidence_storage,
    )
    caption = models.CharField(max_length=220, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=100)
    visibility = models.CharField(
        max_length=24,
        choices=ConstructionEvidenceVisibility.choices,
        default=ConstructionEvidenceVisibility.PROJECT_STAKEHOLDERS,
    )
    status = models.CharField(
        max_length=16,
        choices=ConstructionEvidenceStatus.choices,
        default=ConstructionEvidenceStatus.ACTIVE,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "status", "created_at"]),
            models.Index(fields=["milestone", "created_at"]),
            models.Index(fields=["progress_update", "created_at"]),
            models.Index(fields=["uploaded_by", "created_at"]),
        ]


class ConstructionMilestoneInspection(BaseModel):
    milestone = models.ForeignKey(
        ConstructionMilestone,
        on_delete=models.CASCADE,
        related_name="inspection_links",
    )
    inspection_request = models.ForeignKey(
        InspectionRequest,
        on_delete=models.PROTECT,
        related_name="construction_milestone_links",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="construction_milestone_inspection_links",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["milestone", "created_at"]),
            models.Index(fields=["inspection_request", "created_at"]),
        ]


class ConstructionTimelineEvent(BaseModel):
    project = models.ForeignKey(
        ConstructionProject,
        on_delete=models.CASCADE,
        related_name="timeline_events",
    )
    milestone = models.ForeignKey(
        ConstructionMilestone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timeline_events",
    )
    event_type = models.CharField(max_length=80)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="construction_timeline_events",
    )
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_internal = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "created_at"]),
            models.Index(fields=["milestone", "created_at"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["is_internal"]),
        ]
