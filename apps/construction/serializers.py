from __future__ import annotations

from pathlib import Path

from django.conf import settings
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from apps.construction.choices import (
    ConstructionMilestoneStatus,
    ConstructionProjectStatus,
)
from apps.construction.models import (
    ConstructionEvidence,
    ConstructionMilestone,
    ConstructionMilestoneInspection,
    ConstructionProgressUpdate,
    ConstructionProject,
    ConstructionTimelineEvent,
    ProjectStakeholder,
)
from apps.construction.services import user_can_view_evidence
from apps.inspections.choices import InspectionPriority, InspectionType
from apps.inspections.serializers import (
    InspectionRequestSerializer,
    UserSummarySerializer,
    validate_no_html,
)
from apps.properties.serializers import InquiryPropertySummarySerializer

PDF_MAGIC_BYTES = b"%PDF-"


def validate_construction_evidence_file(value):
    content_type = getattr(value, "content_type", "")
    allowed_types = (
        set(settings.CONSTRUCTION_ALLOWED_IMAGE_TYPES)
        | set(settings.CONSTRUCTION_ALLOWED_VIDEO_TYPES)
        | set(settings.CONSTRUCTION_ALLOWED_DOCUMENT_TYPES)
    )
    if content_type not in allowed_types:
        raise serializers.ValidationError(
            f"File must be one of: {', '.join(sorted(allowed_types))}."
        )
    extension = Path(value.name).suffix.lower()
    allowed_extensions = {item.lower() for item in settings.CONSTRUCTION_ALLOWED_EXTENSIONS}
    if extension not in allowed_extensions:
        raise serializers.ValidationError(
            f"File extension must be one of: {', '.join(sorted(allowed_extensions))}."
        )
    if content_type in set(settings.CONSTRUCTION_ALLOWED_IMAGE_TYPES):
        max_size_mb = settings.CONSTRUCTION_MAX_IMAGE_SIZE_MB
    elif content_type in set(settings.CONSTRUCTION_ALLOWED_VIDEO_TYPES):
        max_size_mb = settings.CONSTRUCTION_MAX_VIDEO_SIZE_MB
    else:
        max_size_mb = settings.CONSTRUCTION_MAX_DOCUMENT_SIZE_MB
    if value.size > max_size_mb * 1024 * 1024:
        raise serializers.ValidationError(f"File must be {max_size_mb}MB or smaller.")
    if content_type == "application/pdf":
        header = value.read(len(PDF_MAGIC_BYTES))
        value.seek(0)
        if header != PDF_MAGIC_BYTES:
            raise serializers.ValidationError("Uploaded file must be a valid PDF.")
        return value
    if content_type.startswith("image/"):
        try:
            image = Image.open(value)
            image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise serializers.ValidationError("Uploaded file must be a valid image.") from exc
        finally:
            value.seek(0)
        return value
    if content_type == "video/mp4":
        header = value.read(16)
        value.seek(0)
        if b"ftyp" not in header:
            raise serializers.ValidationError("Uploaded video must be a valid MP4.")
    if content_type == "video/webm":
        header = value.read(4)
        value.seek(0)
        if not header.startswith(b"\x1a\x45\xdf\xa3"):
            raise serializers.ValidationError("Uploaded video must be a valid WebM.")
    return value


class ConstructionProjectSummarySerializer(serializers.ModelSerializer):
    property = InquiryPropertySummarySerializer(read_only=True)

    class Meta:
        model = ConstructionProject
        fields = [
            "id",
            "property",
            "name",
            "slug",
            "project_type",
            "status",
            "overall_progress",
            "planned_start_date",
            "planned_end_date",
            "created_at",
        ]
        read_only_fields = fields


class ProjectStakeholderSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    invited_by_email = serializers.EmailField(source="invited_by.email", read_only=True)

    class Meta:
        model = ProjectStakeholder
        fields = [
            "id",
            "project",
            "user",
            "user_email",
            "stakeholder_role",
            "access_level",
            "status",
            "invited_by",
            "invited_by_email",
            "invited_at",
            "accepted_at",
            "revoked_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "invited_by",
            "invited_by_email",
            "invited_at",
            "accepted_at",
            "revoked_at",
            "created_at",
            "updated_at",
        ]


class ConstructionMilestoneSerializer(serializers.ModelSerializer):
    inspection_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ConstructionMilestone
        fields = [
            "id",
            "project",
            "name",
            "description",
            "sequence",
            "weight",
            "status",
            "planned_start_date",
            "planned_end_date",
            "actual_start_date",
            "actual_end_date",
            "progress_percent",
            "requires_inspection",
            "blocking",
            "depends_on",
            "notes",
            "inspection_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "status",
            "actual_start_date",
            "actual_end_date",
            "progress_percent",
            "inspection_count",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs: dict) -> dict:
        for field in ["name", "description", "notes"]:
            if field in attrs:
                validate_no_html(str(attrs.get(field) or ""), field)
        return attrs


class ConstructionMilestoneProgressSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ConstructionMilestoneStatus.choices, required=False)
    progress_percent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0,
        max_value=100,
        required=False,
    )
    correction_reason = serializers.CharField(required=False, allow_blank=True, max_length=1200)

    def validate(self, attrs: dict) -> dict:
        if not attrs:
            raise serializers.ValidationError("Provide status or progress_percent.")
        return attrs


class ConstructionEvidenceSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=True)
    signed_url = serializers.SerializerMethodField()
    uploaded_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = ConstructionEvidence
        fields = [
            "id",
            "project",
            "milestone",
            "progress_update",
            "uploaded_by",
            "evidence_type",
            "file",
            "signed_url",
            "caption",
            "captured_at",
            "file_size",
            "mime_type",
            "visibility",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "uploaded_by",
            "signed_url",
            "file_size",
            "mime_type",
            "status",
            "created_at",
            "updated_at",
        ]

    def get_signed_url(self, obj) -> str:
        request = self.context.get("request")
        if request and user_can_view_evidence(request.user, obj):
            return obj.file.url
        return ""

    def validate_file(self, value):
        return validate_construction_evidence_file(value)

    def validate(self, attrs: dict) -> dict:
        project = self.context["project"]
        milestone = attrs.get("milestone")
        progress_update = attrs.get("progress_update")
        if milestone and milestone.project_id != project.id:
            raise serializers.ValidationError({"milestone": ["Milestone is not in this project."]})
        if progress_update and progress_update.project_id != project.id:
            raise serializers.ValidationError(
                {"progress_update": ["Progress update is not in this project."]}
            )
        for field in ["caption"]:
            if field in attrs:
                validate_no_html(str(attrs.get(field) or ""), field)
        return attrs

    def create(self, validated_data):
        file_obj = validated_data["file"]
        validated_data["file_size"] = file_obj.size
        validated_data["mime_type"] = getattr(file_obj, "content_type", "")
        return ConstructionEvidence.objects.create(
            project=self.context["project"],
            uploaded_by=self.context["request"].user,
            **validated_data,
        )


class ConstructionProgressUpdateSerializer(serializers.ModelSerializer):
    submitted_by = UserSummarySerializer(read_only=True)
    evidence = ConstructionEvidenceSerializer(many=True, read_only=True)

    class Meta:
        model = ConstructionProgressUpdate
        fields = [
            "id",
            "project",
            "milestone",
            "submitted_by",
            "title",
            "summary",
            "work_completed",
            "current_progress",
            "issues",
            "blockers",
            "next_steps",
            "reporting_period_start",
            "reporting_period_end",
            "status",
            "submitted_at",
            "reviewed_at",
            "reviewed_by",
            "rejection_reason",
            "correction_reason",
            "evidence",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project",
            "submitted_by",
            "status",
            "submitted_at",
            "reviewed_at",
            "reviewed_by",
            "rejection_reason",
            "evidence",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs: dict) -> dict:
        project = self.context["project"]
        milestone = attrs.get("milestone")
        if milestone and milestone.project_id != project.id:
            raise serializers.ValidationError({"milestone": ["Milestone is not in this project."]})
        for field in [
            "title",
            "summary",
            "work_completed",
            "issues",
            "blockers",
            "next_steps",
            "correction_reason",
        ]:
            if field in attrs:
                validate_no_html(str(attrs.get(field) or ""), field)
        return attrs


class ConstructionProjectSerializer(serializers.ModelSerializer):
    property = InquiryPropertySummarySerializer(read_only=True)
    property_id = serializers.UUIDField(write_only=True, required=True)
    owner = UserSummarySerializer(read_only=True)
    created_by = UserSummarySerializer(read_only=True)
    project_manager = UserSummarySerializer(read_only=True)
    project_manager_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    milestones = ConstructionMilestoneSerializer(many=True, read_only=True)
    stakeholders = ProjectStakeholderSerializer(many=True, read_only=True)

    class Meta:
        model = ConstructionProject
        fields = [
            "id",
            "property",
            "property_id",
            "name",
            "slug",
            "description",
            "project_type",
            "status",
            "visibility",
            "planned_start_date",
            "planned_end_date",
            "actual_start_date",
            "actual_end_date",
            "overall_progress",
            "owner",
            "created_by",
            "project_manager",
            "project_manager_id",
            "contractor_name_or_reference",
            "estimated_duration_days",
            "current_milestone",
            "archived_at",
            "milestones",
            "stakeholders",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "status",
            "actual_start_date",
            "actual_end_date",
            "overall_progress",
            "owner",
            "created_by",
            "project_manager",
            "current_milestone",
            "archived_at",
            "milestones",
            "stakeholders",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs: dict) -> dict:
        for field in [
            "name",
            "description",
            "contractor_name_or_reference",
        ]:
            if field in attrs:
                validate_no_html(str(attrs.get(field) or ""), field)
        return attrs


class ProjectStatusTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ConstructionProjectStatus.choices)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1200)


class ProgressDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1200)


class MilestoneInspectionRequestSerializer(serializers.Serializer):
    purpose = serializers.CharField(max_length=180)
    description = serializers.CharField(required=False, allow_blank=True)
    preferred_date = serializers.DateField(required=False, allow_null=True)
    alternative_date = serializers.DateField(required=False, allow_null=True)
    contact_phone = serializers.CharField(max_length=40)
    contact_email = serializers.EmailField()
    access_notes = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=InspectionPriority.choices, required=False)
    inspection_type = serializers.ChoiceField(
        choices=InspectionType.choices,
        default=InspectionType.CONSTRUCTION_PROGRESS,
    )


class ConstructionMilestoneInspectionSerializer(serializers.ModelSerializer):
    inspection_request = InspectionRequestSerializer(read_only=True)

    class Meta:
        model = ConstructionMilestoneInspection
        fields = ["id", "milestone", "inspection_request", "requested_by", "notes", "created_at"]
        read_only_fields = fields


class ConstructionTimelineEventSerializer(serializers.ModelSerializer):
    actor_label = serializers.SerializerMethodField()

    class Meta:
        model = ConstructionTimelineEvent
        fields = [
            "id",
            "project",
            "milestone",
            "event_type",
            "actor_label",
            "description",
            "metadata",
            "is_internal",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_label(self, obj) -> str:
        if obj.actor:
            return obj.actor.full_name or obj.actor.email
        return "System"


class ConstructionDashboardSerializer(serializers.Serializer):
    stats = serializers.ListField(child=serializers.DictField())
    projects = ConstructionProjectSummarySerializer(many=True)
    delayed_projects = ConstructionProjectSummarySerializer(many=True)
    pending_updates = ConstructionProgressUpdateSerializer(many=True)
    activity = ConstructionTimelineEventSerializer(many=True)
