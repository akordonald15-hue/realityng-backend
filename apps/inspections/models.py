from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import BaseModel
from apps.inspections.choices import (
    ACTIVE_INSPECTION_REQUEST_STATUSES,
    AssignmentStatus,
    EvidenceCategory,
    EvidenceType,
    EvidenceVisibility,
    InspectionCondition,
    InspectionPriority,
    InspectionReportStatus,
    InspectionRequestStatus,
    InspectionRiskLevel,
    InspectionType,
    InspectorAvailabilityStatus,
    InspectorVerificationStatus,
    WalkthroughStatus,
)
from apps.inspections.storage import (
    get_inspection_evidence_storage,
    get_inspection_report_storage,
    get_walkthrough_storage,
)
from apps.properties.models import Property


def walkthrough_upload_to(instance: PropertyWalkthrough, filename: str) -> str:
    return f"properties/{instance.property_id}/walkthroughs/{filename}"


def walkthrough_thumbnail_upload_to(instance: PropertyWalkthrough, filename: str) -> str:
    return f"properties/{instance.property_id}/walkthroughs/thumbnails/{filename}"


def inspection_report_upload_to(instance: InspectionReport, filename: str) -> str:
    return f"inspections/{instance.inspection_request_id}/reports/{filename}"


def inspection_evidence_upload_to(instance: InspectionEvidence, filename: str) -> str:
    return f"inspections/{instance.inspection_report_id}/evidence/{filename}"


class InspectionRequest(BaseModel):
    VALID_STATUS_TRANSITIONS = {
        InspectionRequestStatus.REQUESTED: {
            InspectionRequestStatus.UNDER_REVIEW,
            InspectionRequestStatus.NEEDS_MORE_INFORMATION,
            InspectionRequestStatus.APPROVED,
            InspectionRequestStatus.CANCELLED,
            InspectionRequestStatus.REJECTED,
            InspectionRequestStatus.EXPIRED,
        },
        InspectionRequestStatus.UNDER_REVIEW: {
            InspectionRequestStatus.NEEDS_MORE_INFORMATION,
            InspectionRequestStatus.APPROVED,
            InspectionRequestStatus.CANCELLED,
            InspectionRequestStatus.REJECTED,
        },
        InspectionRequestStatus.NEEDS_MORE_INFORMATION: {
            InspectionRequestStatus.UNDER_REVIEW,
            InspectionRequestStatus.CANCELLED,
            InspectionRequestStatus.REJECTED,
        },
        InspectionRequestStatus.APPROVED: {
            InspectionRequestStatus.ASSIGNED,
            InspectionRequestStatus.SCHEDULED,
            InspectionRequestStatus.CANCELLED,
        },
        InspectionRequestStatus.ASSIGNED: {
            InspectionRequestStatus.SCHEDULED,
            InspectionRequestStatus.CANCELLED,
        },
        InspectionRequestStatus.SCHEDULED: {
            InspectionRequestStatus.IN_PROGRESS,
            InspectionRequestStatus.CANCELLED,
        },
        InspectionRequestStatus.IN_PROGRESS: {
            InspectionRequestStatus.REPORT_SUBMITTED,
            InspectionRequestStatus.CANCELLED,
        },
        InspectionRequestStatus.REPORT_SUBMITTED: {
            InspectionRequestStatus.REPORT_UNDER_REVIEW,
            InspectionRequestStatus.COMPLETED,
        },
        InspectionRequestStatus.REPORT_UNDER_REVIEW: {
            InspectionRequestStatus.REPORT_SUBMITTED,
            InspectionRequestStatus.COMPLETED,
            InspectionRequestStatus.REJECTED,
        },
        InspectionRequestStatus.COMPLETED: set(),
        InspectionRequestStatus.CANCELLED: {InspectionRequestStatus.REQUESTED},
        InspectionRequestStatus.REJECTED: {InspectionRequestStatus.REQUESTED},
        InspectionRequestStatus.EXPIRED: set(),
    }

    property = models.ForeignKey(
        Property,
        on_delete=models.PROTECT,
        related_name="inspection_requests",
    )
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inspection_requests",
    )
    inspection_type = models.CharField(
        max_length=40,
        choices=InspectionType.choices,
        default=InspectionType.GENERAL,
    )
    purpose = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    preferred_date = models.DateField(null=True, blank=True)
    alternative_date = models.DateField(null=True, blank=True)
    contact_phone = models.CharField(max_length=40)
    contact_email = models.EmailField()
    access_notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=32,
        choices=InspectionRequestStatus.choices,
        default=InspectionRequestStatus.REQUESTED,
        db_index=True,
    )
    priority = models.CharField(
        max_length=20,
        choices=InspectionPriority.choices,
        default=InspectionPriority.NORMAL,
    )
    assigned_inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_inspection_requests",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_inspection_operations",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default="Africa/Lagos")
    estimated_duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    access_instructions = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    report_submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["requester", "status", "created_at"]),
            models.Index(fields=["property", "status", "created_at"]),
            models.Index(fields=["assigned_inspector", "status", "scheduled_for"]),
            models.Index(fields=["status", "priority", "created_at"]),
            models.Index(fields=["inspection_type", "status"]),
            models.Index(fields=["scheduled_for"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["property", "requester"],
                condition=Q(status__in=ACTIVE_INSPECTION_REQUEST_STATUSES, deleted_at__isnull=True),
                name="unique_active_inspection_request_per_user_property",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_inspection_type_display()} inspection for {self.property.title}"

    def can_transition_to(self, next_status: str) -> bool:
        return next_status in self.VALID_STATUS_TRANSITIONS.get(self.status, set())

    def transition_to(self, next_status: str, *, update_timestamps: bool = True) -> None:
        if next_status == self.status:
            return
        if not self.can_transition_to(next_status):
            raise ValueError(f"Inspection cannot move from {self.status} to {next_status}.")
        self.status = next_status
        update_fields = ["status", "updated_at"]
        now = timezone.now()
        if update_timestamps:
            if next_status == InspectionRequestStatus.IN_PROGRESS:
                self.started_at = now
                update_fields.append("started_at")
            elif next_status == InspectionRequestStatus.REPORT_SUBMITTED:
                self.report_submitted_at = now
                update_fields.append("report_submitted_at")
            elif next_status == InspectionRequestStatus.COMPLETED:
                self.completed_at = now
                update_fields.append("completed_at")
            elif next_status == InspectionRequestStatus.CANCELLED:
                self.cancelled_at = now
                update_fields.append("cancelled_at")
            elif next_status == InspectionRequestStatus.REJECTED:
                self.rejected_at = now
                update_fields.append("rejected_at")
        self.save(update_fields=update_fields)


class InspectorProfile(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inspector_profile",
    )
    display_name = models.CharField(max_length=160)
    professional_title = models.CharField(max_length=160, blank=True)
    bio = models.TextField(blank=True)
    inspection_types = models.JSONField(default=list, blank=True)
    service_areas = models.JSONField(default=list, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=InspectorVerificationStatus.choices,
        default=InspectorVerificationStatus.PENDING,
    )
    availability_status = models.CharField(
        max_length=20,
        choices=InspectorAvailabilityStatus.choices,
        default=InspectorAvailabilityStatus.AVAILABLE,
    )
    active = models.BooleanField(default=False)
    average_rating_placeholder = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    completed_inspections = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_name"]
        indexes = [
            models.Index(fields=["active", "verification_status", "availability_status"]),
            models.Index(fields=["display_name"]),
        ]

    def __str__(self) -> str:
        return self.display_name


class InspectionAssignment(BaseModel):
    inspection_request = models.ForeignKey(
        InspectionRequest,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inspection_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_inspection_assignments",
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    decline_reason = models.TextField(blank=True)
    reassigned_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reassignments",
    )
    status = models.CharField(
        max_length=20,
        choices=AssignmentStatus.choices,
        default=AssignmentStatus.ASSIGNED,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["inspection_request", "status"]),
            models.Index(fields=["inspector", "status", "assigned_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.inspector_id} assigned to {self.inspection_request_id}"

    def accept(self) -> None:
        self.status = AssignmentStatus.ACCEPTED
        self.accepted_at = timezone.now()
        self.save(update_fields=["status", "accepted_at", "updated_at"])

    def decline(self, reason: str = "") -> None:
        self.status = AssignmentStatus.DECLINED
        self.declined_at = timezone.now()
        self.decline_reason = reason
        self.save(update_fields=["status", "declined_at", "decline_reason", "updated_at"])


class PropertyWalkthrough(BaseModel):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="walkthroughs",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="property_walkthroughs",
    )
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    video_file = models.FileField(upload_to=walkthrough_upload_to, storage=get_walkthrough_storage)
    thumbnail = models.ImageField(
        upload_to=walkthrough_thumbnail_upload_to,
        storage=get_walkthrough_storage,
        null=True,
        blank=True,
    )
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=100)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=WalkthroughStatus.choices,
        default=WalkthroughStatus.DRAFT,
        db_index=True,
    )
    moderation_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_property_walkthroughs",
    )
    published_at = models.DateTimeField(null=True, blank=True)
    hidden_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["display_order", "-created_at"]
        indexes = [
            models.Index(fields=["property", "status", "display_order"]),
            models.Index(fields=["uploaded_by", "status", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["property"],
                condition=Q(is_featured=True, deleted_at__isnull=True),
                name="unique_featured_walkthrough_per_property",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def submit(self) -> None:
        self.status = WalkthroughStatus.PENDING_REVIEW
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "submitted_at", "updated_at"])

    def approve(self, *, reviewer) -> None:
        self.status = WalkthroughStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.published_at = self.published_at or timezone.now()
        self.moderation_reason = ""
        self.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "published_at",
                "moderation_reason",
                "updated_at",
            ]
        )

    def reject(self, *, reviewer, reason: str) -> None:
        self.status = WalkthroughStatus.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.moderation_reason = reason
        self.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "moderation_reason",
                "updated_at",
            ]
        )

    def hide(self, *, reviewer, reason: str = "") -> None:
        self.status = WalkthroughStatus.HIDDEN
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.hidden_at = timezone.now()
        self.moderation_reason = reason
        self.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "hidden_at",
                "moderation_reason",
                "updated_at",
            ]
        )


class InspectionReport(BaseModel):
    inspection_request = models.OneToOneField(
        InspectionRequest,
        on_delete=models.CASCADE,
        related_name="report",
    )
    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inspection_reports",
    )
    summary = models.TextField()
    overall_condition = models.CharField(
        max_length=20,
        choices=InspectionCondition.choices,
        default=InspectionCondition.NOT_ASSESSED,
    )
    recommendation = models.TextField(blank=True)
    risk_level = models.CharField(
        max_length=20,
        choices=InspectionRiskLevel.choices,
        default=InspectionRiskLevel.NOT_ASSESSED,
    )
    structural_notes = models.TextField(blank=True)
    electrical_notes = models.TextField(blank=True)
    plumbing_notes = models.TextField(blank=True)
    roofing_notes = models.TextField(blank=True)
    security_notes = models.TextField(blank=True)
    environment_notes = models.TextField(blank=True)
    accessibility_notes = models.TextField(blank=True)
    estimated_repair_notes = models.TextField(blank=True)
    report_document = models.FileField(
        upload_to=inspection_report_upload_to,
        storage=get_inspection_report_storage,
        null=True,
        blank=True,
    )
    report_document_mime_type = models.CharField(max_length=100, blank=True)
    report_document_file_size = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=InspectionReportStatus.choices,
        default=InspectionReportStatus.DRAFT,
        db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_inspection_reports",
    )
    rejection_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["inspector", "status", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Report for {self.inspection_request_id}"

    def submit(self) -> None:
        self.status = InspectionReportStatus.SUBMITTED
        self.submitted_at = timezone.now()
        self.save(update_fields=["status", "submitted_at", "updated_at"])

    def approve(self, *, reviewer) -> None:
        self.status = InspectionReportStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.approved_at = timezone.now()
        self.rejection_reason = ""
        self.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "approved_at",
                "rejection_reason",
                "updated_at",
            ]
        )

    def request_revision(self, *, reviewer, reason: str) -> None:
        self.status = InspectionReportStatus.NEEDS_REVISION
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"]
        )

    def reject(self, *, reviewer, reason: str) -> None:
        self.status = InspectionReportStatus.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"]
        )


class InspectionEvidence(BaseModel):
    inspection_report = models.ForeignKey(
        InspectionReport,
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inspection_evidence_uploads",
    )
    evidence_type = models.CharField(max_length=20, choices=EvidenceType.choices)
    file = models.FileField(
        upload_to=inspection_evidence_upload_to, storage=get_inspection_evidence_storage
    )
    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveIntegerField(default=0)
    caption = models.CharField(max_length=180, blank=True)
    category = models.CharField(
        max_length=32, choices=EvidenceCategory.choices, default=EvidenceCategory.OTHER
    )
    captured_at = models.DateTimeField(null=True, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    visibility = models.CharField(
        max_length=32,
        choices=EvidenceVisibility.choices,
        default=EvidenceVisibility.REQUESTER_VISIBLE,
    )

    class Meta:
        ordering = ["display_order", "created_at"]
        indexes = [
            models.Index(fields=["inspection_report", "category", "display_order"]),
            models.Index(fields=["uploaded_by", "created_at"]),
            models.Index(fields=["visibility"]),
        ]

    def __str__(self) -> str:
        return f"{self.evidence_type} for report {self.inspection_report_id}"


class InspectionTimelineEvent(BaseModel):
    inspection_request = models.ForeignKey(
        InspectionRequest,
        on_delete=models.CASCADE,
        related_name="timeline_events",
    )
    event_type = models.CharField(max_length=80)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspection_timeline_events",
    )
    description = models.CharField(max_length=240, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_internal = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["inspection_request", "created_at"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["is_internal"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} for {self.inspection_request_id}"
