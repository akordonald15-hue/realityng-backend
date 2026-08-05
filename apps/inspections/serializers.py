from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from apps.accounts.services import user_is_admin
from apps.inspections.choices import (
    ACTIVE_INSPECTION_REQUEST_STATUSES,
    InspectionRequestStatus,
    WalkthroughStatus,
)
from apps.inspections.models import (
    InspectionAssignment,
    InspectionEvidence,
    InspectionReport,
    InspectionRequest,
    InspectionTimelineEvent,
    InspectorProfile,
    PropertyWalkthrough,
)
from apps.inspections.services import (
    user_can_upload_walkthrough,
    user_can_view_evidence,
    user_can_view_inspection,
)
from apps.properties.choices import PropertyStatus
from apps.properties.models import Property
from apps.properties.serializers import InquiryPropertySummarySerializer, build_media_url

PDF_MAGIC_BYTES = b"%PDF-"


def validate_no_html(value: str, field_name: str = "value") -> str:
    if "<" in value or ">" in value:
        raise serializers.ValidationError({field_name: ["HTML is not allowed."]})
    return value


def validate_video_file(value):
    allowed_types = set(settings.WALKTHROUGH_ALLOWED_MIME_TYPES)
    content_type = getattr(value, "content_type", "")
    if content_type not in allowed_types:
        raise serializers.ValidationError(
            f"Video must be one of: {', '.join(sorted(allowed_types))}."
        )
    allowed_extensions = {item.lower() for item in settings.WALKTHROUGH_ALLOWED_EXTENSIONS}
    extension = Path(value.name).suffix.lower()
    if extension not in allowed_extensions:
        raise serializers.ValidationError(
            f"Video extension must be one of: {', '.join(sorted(allowed_extensions))}."
        )
    max_size = settings.WALKTHROUGH_MAX_FILE_SIZE_MB * 1024 * 1024
    if value.size > max_size:
        raise serializers.ValidationError(
            f"Video must be {settings.WALKTHROUGH_MAX_FILE_SIZE_MB}MB or smaller."
        )
    header = value.read(16)
    value.seek(0)
    if content_type == "video/mp4" and b"ftyp" not in header:
        raise serializers.ValidationError("Uploaded video must be a valid MP4.")
    if content_type == "video/webm" and not header.startswith(b"\x1a\x45\xdf\xa3"):
        raise serializers.ValidationError("Uploaded video must be a valid WebM.")
    return value


def validate_private_file(value, *, report_file: bool = False):
    allowed_types = (
        settings.INSPECTION_REPORT_ALLOWED_MIME_TYPES
        if report_file
        else settings.INSPECTION_EVIDENCE_ALLOWED_MIME_TYPES
    )
    allowed_extensions = (
        settings.INSPECTION_REPORT_ALLOWED_EXTENSIONS
        if report_file
        else settings.INSPECTION_EVIDENCE_ALLOWED_EXTENSIONS
    )
    max_size_mb = (
        settings.INSPECTION_MAX_REPORT_FILE_SIZE_MB
        if report_file
        else settings.INSPECTION_MAX_EVIDENCE_FILE_SIZE_MB
    )
    content_type = getattr(value, "content_type", "")
    if content_type not in set(allowed_types):
        raise serializers.ValidationError(
            f"File must be one of: {', '.join(sorted(allowed_types))}."
        )
    extension = Path(value.name).suffix.lower()
    if extension not in {item.lower() for item in allowed_extensions}:
        raise serializers.ValidationError(
            f"File extension must be one of: {', '.join(sorted(allowed_extensions))}."
        )
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


class UserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    full_name = serializers.CharField()


class InspectorProfileSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)

    class Meta:
        model = InspectorProfile
        fields = [
            "id",
            "user",
            "display_name",
            "professional_title",
            "bio",
            "inspection_types",
            "service_areas",
            "verification_status",
            "availability_status",
            "active",
            "average_rating_placeholder",
            "completed_inspections",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class InspectionRequestSerializer(serializers.ModelSerializer):
    property_id = serializers.UUIDField(write_only=True)
    property = InquiryPropertySummarySerializer(read_only=True)
    requester = UserSummarySerializer(read_only=True)
    assigned_inspector = UserSummarySerializer(read_only=True)

    class Meta:
        model = InspectionRequest
        fields = [
            "id",
            "property_id",
            "property",
            "requester",
            "inspection_type",
            "purpose",
            "description",
            "preferred_date",
            "alternative_date",
            "contact_phone",
            "contact_email",
            "access_notes",
            "status",
            "priority",
            "assigned_inspector",
            "scheduled_for",
            "timezone",
            "estimated_duration_minutes",
            "access_instructions",
            "started_at",
            "report_submitted_at",
            "completed_at",
            "cancelled_at",
            "rejected_at",
            "rejection_reason",
            "cancellation_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "property",
            "requester",
            "status",
            "priority",
            "assigned_inspector",
            "scheduled_for",
            "timezone",
            "estimated_duration_minutes",
            "access_instructions",
            "started_at",
            "report_submitted_at",
            "completed_at",
            "cancelled_at",
            "rejected_at",
            "rejection_reason",
            "cancellation_reason",
            "created_at",
            "updated_at",
        ]

    def validate_property_id(self, value):
        try:
            prop = Property.objects.select_related("owner").get(id=value)
        except Property.DoesNotExist as exc:
            raise serializers.ValidationError("Property is not available.") from exc
        request = self.context["request"]
        if prop.status != PropertyStatus.APPROVED and prop.owner_id != request.user.id:
            raise serializers.ValidationError("Property is not available for inspections.")
        if prop.owner_id == request.user.id:
            raise serializers.ValidationError(
                "You cannot request an inspection for your own property."
            )
        self.context["property"] = prop
        return value

    def validate(self, attrs):
        request = self.context["request"]
        if not request.user.is_active or request.user.is_suspended:
            raise serializers.ValidationError("Your account cannot create inspection requests.")
        for field in ["purpose", "description", "access_notes"]:
            if field in attrs:
                validate_no_html(str(attrs.get(field) or ""), field)
        preferred_date = attrs.get("preferred_date")
        alternative_date = attrs.get("alternative_date")
        today = timezone.localdate()
        if preferred_date and preferred_date < today:
            raise serializers.ValidationError(
                {"preferred_date": ["Preferred date cannot be in the past."]}
            )
        if alternative_date and alternative_date < today:
            raise serializers.ValidationError(
                {"alternative_date": ["Alternative date cannot be in the past."]}
            )
        prop = self.context.get("property")
        if prop and self.instance is None:
            duplicate = InspectionRequest.objects.filter(
                property=prop,
                requester=request.user,
                status__in=ACTIVE_INSPECTION_REQUEST_STATUSES,
            ).exists()
            if duplicate:
                raise serializers.ValidationError(
                    "You already have an active inspection request for this property."
                )
        return attrs

    def create(self, validated_data):
        validated_data.pop("property_id")
        return InspectionRequest.objects.create(
            property=self.context["property"],
            requester=self.context["request"].user,
            **validated_data,
        )

    def update(self, instance, validated_data):
        allowed = {
            "purpose",
            "description",
            "preferred_date",
            "alternative_date",
            "contact_phone",
            "contact_email",
            "access_notes",
        }
        if instance.status not in [
            InspectionRequestStatus.REQUESTED,
            InspectionRequestStatus.NEEDS_MORE_INFORMATION,
        ]:
            raise serializers.ValidationError("This inspection request can no longer be edited.")
        for field in allowed:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save(
            update_fields=[field for field in allowed if field in validated_data] + ["updated_at"]
        )
        return instance


class AdminInspectionRequestSerializer(InspectionRequestSerializer):
    assigned_by = UserSummarySerializer(read_only=True)

    class Meta(InspectionRequestSerializer.Meta):
        fields = InspectionRequestSerializer.Meta.fields + [
            "assigned_by",
            "assigned_at",
            "admin_notes",
        ]
        read_only_fields = InspectionRequestSerializer.Meta.read_only_fields + [
            "assigned_by",
            "assigned_at",
            "admin_notes",
        ]


class InspectionDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1600)
    message = serializers.CharField(required=False, allow_blank=True, max_length=1600)
    admin_notes = serializers.CharField(required=False, allow_blank=True, max_length=1600)


class InspectionAssignSerializer(serializers.Serializer):
    inspector_id = serializers.UUIDField()
    scheduled_for = serializers.DateTimeField(required=False, allow_null=True)
    timezone = serializers.CharField(required=False, allow_blank=True, max_length=64)
    estimated_duration_minutes = serializers.IntegerField(
        required=False, min_value=15, max_value=480
    )
    access_instructions = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=1600)


class InspectionScheduleSerializer(serializers.Serializer):
    scheduled_for = serializers.DateTimeField()
    timezone = serializers.CharField(required=False, allow_blank=True, max_length=64)
    estimated_duration_minutes = serializers.IntegerField(
        required=False, min_value=15, max_value=480
    )
    access_instructions = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate_scheduled_for(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Schedule must be in the future.")
        return value


class InspectionAssignmentSerializer(serializers.ModelSerializer):
    inspection_request = InspectionRequestSerializer(read_only=True)
    inspector = UserSummarySerializer(read_only=True)
    assigned_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = InspectionAssignment
        fields = [
            "id",
            "inspection_request",
            "inspector",
            "assigned_by",
            "assigned_at",
            "accepted_at",
            "declined_at",
            "decline_reason",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PropertyWalkthroughSerializer(serializers.ModelSerializer):
    video_file = serializers.FileField(write_only=True, required=True)
    thumbnail_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    property = InquiryPropertySummarySerializer(read_only=True)
    uploaded_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = PropertyWalkthrough
        fields = [
            "id",
            "property",
            "uploaded_by",
            "title",
            "description",
            "video_file",
            "video_url",
            "thumbnail",
            "thumbnail_url",
            "duration_seconds",
            "file_size",
            "mime_type",
            "display_order",
            "is_featured",
            "status",
            "moderation_reason",
            "submitted_at",
            "reviewed_at",
            "published_at",
            "hidden_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "property",
            "uploaded_by",
            "video_url",
            "thumbnail_url",
            "file_size",
            "mime_type",
            "status",
            "moderation_reason",
            "submitted_at",
            "reviewed_at",
            "published_at",
            "hidden_at",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.CharField)
    def get_video_url(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if obj.status != WalkthroughStatus.APPROVED and not (user and user_is_admin(user)):
            return ""
        return build_media_url(obj.video_file, request)

    @extend_schema_field(serializers.CharField)
    def get_thumbnail_url(self, obj):
        return build_media_url(obj.thumbnail, self.context.get("request")) if obj.thumbnail else ""

    def validate_video_file(self, value):
        return validate_video_file(value)

    def validate(self, attrs):
        prop = self.context["property"]
        request = self.context["request"]
        if not user_can_upload_walkthrough(request.user, prop):
            raise serializers.ValidationError("You cannot upload walkthroughs for this property.")
        if self.instance is None:
            count = prop.walkthroughs.exclude(status=WalkthroughStatus.ARCHIVED).count()
            if count >= settings.WALKTHROUGH_MAX_VIDEOS_PER_PROPERTY:
                raise serializers.ValidationError(
                    "A property can have at most "
                    f"{settings.WALKTHROUGH_MAX_VIDEOS_PER_PROPERTY} walkthrough videos."
                )
        for field in ["title", "description"]:
            if field in attrs:
                validate_no_html(str(attrs.get(field) or ""), field)
        return attrs

    def create(self, validated_data):
        video = validated_data["video_file"]
        validated_data["file_size"] = video.size
        validated_data["mime_type"] = getattr(video, "content_type", "")
        return PropertyWalkthrough.objects.create(
            property=self.context["property"],
            uploaded_by=self.context["request"].user,
            **validated_data,
        )


class PublicPropertyWalkthroughSerializer(serializers.ModelSerializer):
    video_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = PropertyWalkthrough
        fields = [
            "id",
            "title",
            "description",
            "video_url",
            "thumbnail_url",
            "duration_seconds",
            "display_order",
            "is_featured",
            "published_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField)
    def get_video_url(self, obj):
        return build_media_url(obj.video_file, self.context.get("request"))

    @extend_schema_field(serializers.CharField)
    def get_thumbnail_url(self, obj):
        return build_media_url(obj.thumbnail, self.context.get("request")) if obj.thumbnail else ""


class AdminWalkthroughSerializer(PropertyWalkthroughSerializer):
    reviewed_by = UserSummarySerializer(read_only=True)

    class Meta(PropertyWalkthroughSerializer.Meta):
        fields = PropertyWalkthroughSerializer.Meta.fields + ["reviewed_by"]
        read_only_fields = PropertyWalkthroughSerializer.Meta.read_only_fields + ["reviewed_by"]


class InspectionEvidenceSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=True)
    signed_url = serializers.SerializerMethodField()
    uploaded_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = InspectionEvidence
        fields = [
            "id",
            "evidence_type",
            "file",
            "signed_url",
            "mime_type",
            "file_size",
            "caption",
            "category",
            "captured_at",
            "display_order",
            "visibility",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "signed_url",
            "mime_type",
            "file_size",
            "uploaded_by",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.CharField)
    def get_signed_url(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated and user_can_view_evidence(request.user, obj):
            return obj.file.url
        return ""

    def validate_file(self, value):
        return validate_private_file(value)

    def create(self, validated_data):
        file_obj = validated_data["file"]
        validated_data["file_size"] = file_obj.size
        validated_data["mime_type"] = getattr(file_obj, "content_type", "")
        return InspectionEvidence.objects.create(
            inspection_report=self.context["inspection_report"],
            uploaded_by=self.context["request"].user,
            **validated_data,
        )


class InspectionReportSerializer(serializers.ModelSerializer):
    inspection_request = InspectionRequestSerializer(read_only=True)
    inspector = UserSummarySerializer(read_only=True)
    evidence = InspectionEvidenceSerializer(many=True, read_only=True)
    report_document = serializers.FileField(write_only=True, required=False, allow_null=True)
    report_document_signed_url = serializers.SerializerMethodField()

    class Meta:
        model = InspectionReport
        fields = [
            "id",
            "inspection_request",
            "inspector",
            "summary",
            "overall_condition",
            "recommendation",
            "risk_level",
            "structural_notes",
            "electrical_notes",
            "plumbing_notes",
            "roofing_notes",
            "security_notes",
            "environment_notes",
            "accessibility_notes",
            "estimated_repair_notes",
            "report_document",
            "report_document_signed_url",
            "report_document_mime_type",
            "report_document_file_size",
            "status",
            "submitted_at",
            "reviewed_at",
            "approved_at",
            "rejection_reason",
            "evidence",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "inspection_request",
            "inspector",
            "report_document_signed_url",
            "report_document_mime_type",
            "report_document_file_size",
            "status",
            "submitted_at",
            "reviewed_at",
            "approved_at",
            "rejection_reason",
            "evidence",
            "created_at",
            "updated_at",
        ]

    @extend_schema_field(serializers.CharField)
    def get_report_document_signed_url(self, obj):
        request = self.context.get("request")
        if not obj.report_document:
            return ""
        if (
            request
            and request.user.is_authenticated
            and user_can_view_inspection(request.user, obj.inspection_request)
        ):
            return obj.report_document.url
        return ""

    def validate_report_document(self, value):
        if value:
            return validate_private_file(value, report_file=True)
        return value

    def validate(self, attrs):
        for field in [
            "summary",
            "recommendation",
            "structural_notes",
            "electrical_notes",
            "plumbing_notes",
            "roofing_notes",
            "security_notes",
            "environment_notes",
            "accessibility_notes",
            "estimated_repair_notes",
        ]:
            if field in attrs:
                validate_no_html(str(attrs.get(field) or ""), field)
        return attrs

    def create(self, validated_data):
        document = validated_data.get("report_document")
        if document:
            validated_data["report_document_mime_type"] = getattr(document, "content_type", "")
            validated_data["report_document_file_size"] = document.size
        return InspectionReport.objects.create(
            inspection_request=self.context["inspection_request"],
            inspector=self.context["request"].user,
            **validated_data,
        )

    def update(self, instance, validated_data):
        document = validated_data.get("report_document")
        if document:
            validated_data["report_document_mime_type"] = getattr(document, "content_type", "")
            validated_data["report_document_file_size"] = document.size
        return super().update(instance, validated_data)


class AdminReportDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=1600)


class InspectionTimelineEventSerializer(serializers.ModelSerializer):
    actor_label = serializers.SerializerMethodField()

    class Meta:
        model = InspectionTimelineEvent
        fields = ["id", "event_type", "description", "actor_label", "metadata", "created_at"]
        read_only_fields = fields

    def get_actor_label(self, obj):
        if not obj.actor:
            return "RealityNG"
        if user_is_admin(obj.actor):
            return "RealityNG operations"
        return obj.actor.full_name or obj.actor.email


class InspectionDashboardSerializer(serializers.Serializer):
    stats = serializers.ListField(child=serializers.DictField())
    recent_requests = InspectionRequestSerializer(many=True)
    pending_assignments = InspectionAssignmentSerializer(many=True, required=False)
    pending_walkthroughs = AdminWalkthroughSerializer(many=True, required=False)
    pending_reports = InspectionReportSerializer(many=True, required=False)
