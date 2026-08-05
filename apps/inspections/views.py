from __future__ import annotations

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.services import user_is_admin
from apps.inspections.choices import (
    AssignmentStatus,
    InspectionReportStatus,
    InspectionRequestStatus,
    WalkthroughStatus,
)
from apps.inspections.models import (
    InspectionAssignment,
    InspectionEvidence,
    InspectionReport,
    InspectionRequest,
    InspectorProfile,
    PropertyWalkthrough,
)
from apps.inspections.permissions import IsInspectionAdmin, IsInspector
from apps.inspections.serializers import (
    AdminInspectionRequestSerializer,
    AdminReportDecisionSerializer,
    AdminWalkthroughSerializer,
    InspectionAssignmentSerializer,
    InspectionAssignSerializer,
    InspectionDashboardSerializer,
    InspectionDecisionSerializer,
    InspectionEvidenceSerializer,
    InspectionReportSerializer,
    InspectionRequestSerializer,
    InspectionScheduleSerializer,
    InspectionTimelineEventSerializer,
    InspectorProfileSerializer,
    PropertyWalkthroughSerializer,
    PublicPropertyWalkthroughSerializer,
)
from apps.inspections.services import (
    create_timeline_event,
    emit_inspection_event,
    inspection_queryset_for_user,
    public_walkthrough_queryset,
    user_can_upload_walkthrough,
    user_can_view_evidence,
    user_can_view_inspection,
    user_is_inspector,
)
from apps.properties.models import Property


class ActionScopedThrottleMixin:
    throttle_scope_by_action: dict[str, str] = {}
    throttle_classes = [AnonRateThrottle, UserRateThrottle, ScopedRateThrottle]

    def get_throttles(self):
        if getattr(self, "action", None) in self.throttle_scope_by_action:
            self.throttle_scope = self.throttle_scope_by_action[self.action]
        return super().get_throttles()


def filter_inspection_requests(queryset, request):
    for field in ["status", "inspection_type", "priority"]:
        value = request.query_params.get(field)
        if value:
            queryset = queryset.filter(**{field: value})
    property_id = request.query_params.get("property")
    if property_id:
        queryset = queryset.filter(property_id=property_id)
    requester = request.query_params.get("requester")
    if requester:
        queryset = queryset.filter(requester_id=requester)
    inspector = request.query_params.get("inspector")
    if inspector:
        queryset = queryset.filter(assigned_inspector_id=inspector)
    for field in ["state", "city", "lga"]:
        value = request.query_params.get(field)
        if value:
            queryset = queryset.filter(**{f"property__{field}__iexact": value})
    return queryset.order_by("-created_at")


class InspectionRequestViewSet(
    ActionScopedThrottleMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = InspectionRequestSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope_by_action = {
        "create": "inspection_request_create",
        "cancel": "inspection_request_transition",
        "provide_information": "inspection_request_transition",
        "schedule": "inspection_schedule",
        "reschedule": "inspection_schedule",
        "start": "inspection_request_transition",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return InspectionRequest.objects.none()
        return filter_inspection_requests(
            inspection_queryset_for_user(self.request.user), self.request
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inspection = serializer.save()
        emit_inspection_event(
            actor=request.user,
            action="inspection_request.created",
            entity=inspection,
            metadata={"property_id": str(inspection.property_id), "status": inspection.status},
        )
        create_timeline_event(
            inspection_request=inspection,
            event_type="InspectionRequested",
            actor=request.user,
            description="Inspection request submitted.",
        )
        return Response(self.get_serializer(inspection).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        queryset = self.filter_queryset(self.get_queryset().filter(requester=request.user))
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        inspection = self.get_object()
        if inspection.requester_id != request.user.id and not user_is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = InspectionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not inspection.can_transition_to(InspectionRequestStatus.CANCELLED):
            return Response({"detail": "This inspection cannot be cancelled."}, status=400)
        inspection.cancellation_reason = serializer.validated_data.get("reason", "")
        inspection.save(update_fields=["cancellation_reason", "updated_at"])
        inspection.transition_to(InspectionRequestStatus.CANCELLED)
        emit_inspection_event(
            actor=request.user, action="inspection_request.cancelled", entity=inspection
        )
        create_timeline_event(
            inspection_request=inspection,
            event_type="InspectionCancelled",
            actor=request.user,
            description="Inspection request cancelled.",
        )
        return Response(self.get_serializer(inspection).data)

    @action(detail=True, methods=["post"], url_path="provide-information")
    def provide_information(self, request, pk=None):
        inspection = self.get_object()
        if inspection.requester_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = InspectionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.validated_data.get("message", "")
        if message:
            inspection.description = (
                f"{inspection.description}\n\nAdditional information: {message}".strip()
            )
            inspection.save(update_fields=["description", "updated_at"])
        if inspection.status == InspectionRequestStatus.NEEDS_MORE_INFORMATION:
            inspection.transition_to(InspectionRequestStatus.UNDER_REVIEW)
        emit_inspection_event(
            actor=request.user, action="inspection_request.information_provided", entity=inspection
        )
        create_timeline_event(
            inspection_request=inspection,
            event_type="InspectionInformationProvided",
            actor=request.user,
            description="Additional information provided.",
        )
        return Response(self.get_serializer(inspection).data)

    @action(detail=True, methods=["post"])
    def schedule(self, request, pk=None):
        inspection = self.get_object()
        if inspection.assigned_inspector_id != request.user.id and not user_is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = InspectionScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(inspection, field, value)
        if inspection.can_transition_to(InspectionRequestStatus.SCHEDULED):
            inspection.transition_to(InspectionRequestStatus.SCHEDULED, update_timestamps=False)
        inspection.save(update_fields=[*serializer.validated_data.keys(), "updated_at"])
        emit_inspection_event(
            actor=request.user, action="inspection_request.scheduled", entity=inspection
        )
        create_timeline_event(
            inspection_request=inspection,
            event_type="InspectionScheduled",
            actor=request.user,
            description="Inspection schedule confirmed.",
        )
        return Response(self.get_serializer(inspection).data)

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None):
        return self.schedule(request, pk)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        inspection = self.get_object()
        if inspection.assigned_inspector_id != request.user.id and not user_is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        try:
            inspection.transition_to(InspectionRequestStatus.IN_PROGRESS)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        emit_inspection_event(
            actor=request.user, action="inspection_request.started", entity=inspection
        )
        create_timeline_event(
            inspection_request=inspection,
            event_type="InspectionStarted",
            actor=request.user,
            description="Inspection started.",
        )
        return Response(self.get_serializer(inspection).data)

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        inspection = self.get_object()
        events = inspection.timeline_events.filter(is_internal=False)
        return Response(
            InspectionTimelineEventSerializer(events, many=True, context={"request": request}).data
        )

    @action(detail=True, methods=["get"])
    def report(self, request, pk=None):
        inspection = self.get_object()
        report = get_object_or_404(
            InspectionReport.objects.prefetch_related("evidence"), inspection_request=inspection
        )
        if report.status != InspectionReportStatus.APPROVED and not (
            user_is_admin(request.user) or report.inspector_id == request.user.id
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(InspectionReportSerializer(report, context={"request": request}).data)


class AdminInspectionRequestViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdminInspectionRequestSerializer
    permission_classes = [IsAuthenticated, IsInspectionAdmin]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return InspectionRequest.objects.none()
        return filter_inspection_requests(
            inspection_queryset_for_user(self.request.user), self.request
        )

    def _decision_serializer(self, request):
        serializer = InspectionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer

    def _transition(self, request, inspection, next_status, event, description=""):
        try:
            inspection.transition_to(next_status)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        emit_inspection_event(
            actor=request.user,
            action=event,
            entity=inspection,
            metadata={"status": inspection.status},
        )
        create_timeline_event(
            inspection_request=inspection,
            event_type=event.title().replace(".", ""),
            actor=request.user,
            description=description or event,
        )
        return Response(self.get_serializer(inspection).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        inspection = self.get_object()
        if inspection.status == InspectionRequestStatus.REQUESTED:
            inspection.transition_to(InspectionRequestStatus.UNDER_REVIEW)
        return self._transition(
            request,
            inspection,
            InspectionRequestStatus.APPROVED,
            "inspection_request.approved",
            "Inspection approved.",
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        inspection = self.get_object()
        serializer = self._decision_serializer(request)
        reason = serializer.validated_data.get("reason", "").strip()
        if not reason:
            return Response({"reason": ["Rejection reason is required."]}, status=400)
        inspection.rejection_reason = reason
        inspection.save(update_fields=["rejection_reason", "updated_at"])
        return self._transition(
            request,
            inspection,
            InspectionRequestStatus.REJECTED,
            "inspection_request.rejected",
            "Inspection rejected.",
        )

    @action(detail=True, methods=["post"], url_path="request-information")
    def request_information(self, request, pk=None):
        inspection = self.get_object()
        serializer = self._decision_serializer(request)
        inspection.admin_notes = serializer.validated_data.get("admin_notes", "")
        inspection.save(update_fields=["admin_notes", "updated_at"])
        return self._transition(
            request,
            inspection,
            InspectionRequestStatus.NEEDS_MORE_INFORMATION,
            "inspection_request.more_info_requested",
            "RealityNG requested more information.",
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        inspection = self.get_object()
        serializer = self._decision_serializer(request)
        inspection.cancellation_reason = serializer.validated_data.get("reason", "")
        inspection.save(update_fields=["cancellation_reason", "updated_at"])
        return self._transition(
            request,
            inspection,
            InspectionRequestStatus.CANCELLED,
            "inspection_request.cancelled",
            "Inspection cancelled.",
        )

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        inspection = self.get_object()
        return self._transition(
            request,
            inspection,
            InspectionRequestStatus.REQUESTED,
            "inspection_request.reopened",
            "Inspection reopened.",
        )

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        inspection = self.get_object()
        serializer = InspectionAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inspector = get_object_or_404(User, id=serializer.validated_data["inspector_id"])
        if not user_is_inspector(inspector):
            return Response({"inspector_id": ["Select an active approved inspector."]}, status=400)
        previous_assignment = inspection.assignments.filter(
            status__in=[AssignmentStatus.ASSIGNED, AssignmentStatus.ACCEPTED]
        ).first()
        assignment = InspectionAssignment.objects.create(
            inspection_request=inspection,
            inspector=inspector,
            assigned_by=request.user,
            reassigned_from=previous_assignment,
            notes=serializer.validated_data.get("notes", ""),
        )
        if previous_assignment:
            previous_assignment.status = AssignmentStatus.REASSIGNED
            previous_assignment.save(update_fields=["status", "updated_at"])
        inspection.assigned_inspector = inspector
        inspection.assigned_by = request.user
        inspection.assigned_at = timezone.now()
        for field in [
            "scheduled_for",
            "timezone",
            "estimated_duration_minutes",
            "access_instructions",
        ]:
            if field in serializer.validated_data:
                setattr(inspection, field, serializer.validated_data[field])
        if inspection.status == InspectionRequestStatus.REQUESTED:
            inspection.transition_to(InspectionRequestStatus.UNDER_REVIEW)
        if inspection.status == InspectionRequestStatus.UNDER_REVIEW:
            inspection.transition_to(InspectionRequestStatus.APPROVED)
        if inspection.can_transition_to(InspectionRequestStatus.ASSIGNED):
            inspection.status = InspectionRequestStatus.ASSIGNED
        inspection.save()
        emit_inspection_event(
            actor=request.user,
            action="inspection_request.inspector_assigned",
            entity=inspection,
            metadata={"inspector_id": str(inspector.id), "assignment_id": str(assignment.id)},
        )
        create_timeline_event(
            inspection_request=inspection,
            event_type="InspectorAssigned",
            actor=request.user,
            description="Inspector assigned.",
        )
        return Response(
            InspectionAssignmentSerializer(assignment, context={"request": request}).data
        )


class InspectorProfileViewSet(viewsets.ModelViewSet):
    serializer_class = InspectorProfileSerializer
    permission_classes = [IsAuthenticated, IsInspectionAdmin]

    def get_queryset(self):
        return InspectorProfile.objects.select_related("user")


class InspectionAssignmentViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = InspectionAssignmentSerializer
    permission_classes = [IsAuthenticated, IsInspector]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return InspectionAssignment.objects.none()
        queryset = InspectionAssignment.objects.select_related(
            "inspection_request",
            "inspection_request__property",
            "inspection_request__requester",
            "inspector",
            "assigned_by",
        )
        if user_is_admin(self.request.user):
            return queryset
        return queryset.filter(inspector=self.request.user)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        assignment = self.get_object()
        if assignment.inspector_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        assignment.accept()
        inspection = assignment.inspection_request
        inspection.assigned_inspector = request.user
        inspection.assigned_at = assignment.assigned_at
        if inspection.can_transition_to(InspectionRequestStatus.ASSIGNED):
            inspection.status = InspectionRequestStatus.ASSIGNED
        inspection.save(update_fields=["assigned_inspector", "assigned_at", "status", "updated_at"])
        emit_inspection_event(
            actor=request.user, action="inspection_assignment.accepted", entity=assignment
        )
        create_timeline_event(
            inspection_request=inspection,
            event_type="InspectorAccepted",
            actor=request.user,
            description="Inspector accepted assignment.",
        )
        return Response(self.get_serializer(assignment).data)

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        assignment = self.get_object()
        if assignment.inspector_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = InspectionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment.decline(serializer.validated_data.get("reason", ""))
        emit_inspection_event(
            actor=request.user, action="inspection_assignment.declined", entity=assignment
        )
        create_timeline_event(
            inspection_request=assignment.inspection_request,
            event_type="InspectorDeclined",
            actor=request.user,
            description="Inspector declined assignment.",
        )
        return Response(self.get_serializer(assignment).data)


class PropertyWalkthroughManagementViewSet(ActionScopedThrottleMixin, viewsets.ModelViewSet):
    serializer_class = PropertyWalkthroughSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope_by_action = {
        "create": "walkthrough_upload",
        "submit": "walkthrough_submit",
        "set_featured": "walkthrough_submit",
        "reorder": "walkthrough_submit",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PropertyWalkthrough.objects.none()
        queryset = PropertyWalkthrough.objects.select_related(
            "property", "uploaded_by", "reviewed_by"
        )
        if user_is_admin(self.request.user):
            return queryset
        return queryset.filter(
            Q(uploaded_by=self.request.user) | Q(property__owner=self.request.user)
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        property_id = self.kwargs.get("property_id") or self.request.data.get("property_id")
        if property_id:
            context["property"] = get_object_or_404(
                Property.objects.select_related("owner"), id=property_id
            )
        return context

    def create(self, request, *args, **kwargs):
        prop = get_object_or_404(
            Property.objects.select_related("owner"), id=kwargs.get("property_id")
        )
        serializer = self.get_serializer(
            data=request.data, context={**self.get_serializer_context(), "property": prop}
        )
        serializer.is_valid(raise_exception=True)
        walkthrough = serializer.save()
        emit_inspection_event(
            actor=request.user,
            action="walkthrough.uploaded",
            entity=walkthrough,
            metadata={"property_id": str(prop.id)},
        )
        return Response(
            PropertyWalkthroughSerializer(walkthrough, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def perform_destroy(self, instance):
        emit_inspection_event(
            actor=self.request.user, action="walkthrough.archived", entity=instance
        )
        instance.status = WalkthroughStatus.ARCHIVED
        instance.save(update_fields=["status", "updated_at"])

    @action(detail=False, methods=["get"])
    def manage(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        walkthrough = self.get_object()
        if walkthrough.uploaded_by_id != request.user.id and not user_is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        walkthrough.submit()
        emit_inspection_event(
            actor=request.user, action="walkthrough.submitted", entity=walkthrough
        )
        create_timeline_event(
            inspection_request=InspectionRequest.objects.filter(property=walkthrough.property)
            .order_by("-created_at")
            .first(),
            event_type="WalkthroughSubmitted",
            actor=request.user,
            description="Walkthrough submitted for moderation.",
        ) if InspectionRequest.objects.filter(property=walkthrough.property).exists() else None
        return Response(self.get_serializer(walkthrough).data)

    @action(detail=True, methods=["post"], url_path="set-featured")
    def set_featured(self, request, pk=None):
        walkthrough = self.get_object()
        if not user_can_upload_walkthrough(request.user, walkthrough.property):
            return Response(status=status.HTTP_403_FORBIDDEN)
        PropertyWalkthrough.objects.filter(property=walkthrough.property).exclude(
            pk=walkthrough.pk
        ).update(is_featured=False)
        walkthrough.is_featured = True
        walkthrough.save(update_fields=["is_featured", "updated_at"])
        emit_inspection_event(
            actor=request.user, action="walkthrough.featured_set", entity=walkthrough
        )
        return Response(self.get_serializer(walkthrough).data)

    @action(detail=False, methods=["post"])
    def reorder(self, request):
        items = request.data.get("items", [])
        for item in items:
            PropertyWalkthrough.objects.filter(id=item.get("id")).update(
                display_order=item.get("display_order", 0)
            )
        return Response({"status": "ok"})


class PublicPropertyWalkthroughViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = PublicPropertyWalkthroughSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PropertyWalkthrough.objects.none()
        return (
            public_walkthrough_queryset()
            .filter(property_id=self.kwargs["property_id"])
            .order_by("-is_featured", "display_order", "-published_at")
        )


class AdminWalkthroughViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdminWalkthroughSerializer
    permission_classes = [IsAuthenticated, IsInspectionAdmin]

    def get_queryset(self):
        queryset = PropertyWalkthrough.objects.select_related(
            "property", "uploaded_by", "reviewed_by"
        )
        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset.order_by("-created_at")

    def _decision_reason(self, request, required=False):
        serializer = InspectionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "").strip()
        if required and not reason:
            return Response({"reason": ["Reason is required."]}, status=400)
        return reason

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        walkthrough = self.get_object()
        walkthrough.approve(reviewer=request.user)
        emit_inspection_event(actor=request.user, action="walkthrough.approved", entity=walkthrough)
        return Response(self.get_serializer(walkthrough).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        walkthrough = self.get_object()
        reason = self._decision_reason(request, required=True)
        if isinstance(reason, Response):
            return reason
        walkthrough.reject(reviewer=request.user, reason=reason)
        emit_inspection_event(actor=request.user, action="walkthrough.rejected", entity=walkthrough)
        return Response(self.get_serializer(walkthrough).data)

    @action(detail=True, methods=["post"])
    def hide(self, request, pk=None):
        walkthrough = self.get_object()
        reason = self._decision_reason(request)
        if isinstance(reason, Response):
            return reason
        walkthrough.hide(reviewer=request.user, reason=reason)
        emit_inspection_event(actor=request.user, action="walkthrough.hidden", entity=walkthrough)
        return Response(self.get_serializer(walkthrough).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        walkthrough = self.get_object()
        walkthrough.status = WalkthroughStatus.PENDING_REVIEW
        walkthrough.save(update_fields=["status", "updated_at"])
        emit_inspection_event(actor=request.user, action="walkthrough.restored", entity=walkthrough)
        return Response(self.get_serializer(walkthrough).data)


class InspectionReportViewSet(ActionScopedThrottleMixin, viewsets.ModelViewSet):
    serializer_class = InspectionReportSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope_by_action = {
        "create": "inspection_report_submit",
        "submit": "inspection_report_submit",
        "evidence": "inspection_evidence_upload",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return InspectionReport.objects.none()
        queryset = InspectionReport.objects.select_related(
            "inspection_request",
            "inspection_request__property",
            "inspection_request__requester",
            "inspector",
            "reviewed_by",
        ).prefetch_related("evidence")
        if user_is_admin(self.request.user):
            return queryset
        return queryset.filter(
            Q(inspector=self.request.user)
            | Q(inspection_request__requester=self.request.user)
            | Q(inspection_request__property__owner=self.request.user)
        ).distinct()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        request_id = self.kwargs.get("request_id") or self.request.data.get("inspection_request_id")
        if request_id:
            context["inspection_request"] = get_object_or_404(InspectionRequest, id=request_id)
        return context

    def create(self, request, *args, **kwargs):
        inspection = get_object_or_404(
            InspectionRequest,
            id=kwargs.get("request_id") or request.data.get("inspection_request_id"),
        )
        if inspection.assigned_inspector_id != request.user.id and not user_is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(
            data=request.data,
            context={**self.get_serializer_context(), "inspection_request": inspection},
        )
        serializer.is_valid(raise_exception=True)
        report = serializer.save()
        emit_inspection_event(actor=request.user, action="inspection_report.created", entity=report)
        create_timeline_event(
            inspection_request=inspection,
            event_type="InspectionReportDrafted",
            actor=request.user,
            description="Inspection report drafted.",
        )
        return Response(
            InspectionReportSerializer(report, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        report = self.get_object()
        if report.inspector_id != request.user.id and not user_is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        report.submit()
        inspection = report.inspection_request
        if inspection.status in [
            InspectionRequestStatus.IN_PROGRESS,
            InspectionRequestStatus.SCHEDULED,
        ]:
            inspection.transition_to(InspectionRequestStatus.REPORT_SUBMITTED)
        emit_inspection_event(
            actor=request.user, action="inspection_report.submitted", entity=report
        )
        create_timeline_event(
            inspection_request=inspection,
            event_type="InspectionReportSubmitted",
            actor=request.user,
            description="Inspection report submitted.",
        )
        return Response(self.get_serializer(report).data)

    @action(detail=True, methods=["post"])
    def evidence(self, request, pk=None):
        report = self.get_object()
        if report.inspector_id != request.user.id and not user_is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = InspectionEvidenceSerializer(
            data=request.data, context={"request": request, "inspection_report": report}
        )
        serializer.is_valid(raise_exception=True)
        evidence = serializer.save()
        emit_inspection_event(
            actor=request.user,
            action="inspection_evidence.uploaded",
            entity=evidence,
            metadata={"report_id": str(report.id)},
        )
        create_timeline_event(
            inspection_request=report.inspection_request,
            event_type="InspectionEvidenceUploaded",
            actor=request.user,
            description="Inspection evidence uploaded.",
        )
        return Response(
            InspectionEvidenceSerializer(evidence, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="signed-url")
    def signed_url(self, request, pk=None):
        report = self.get_object()
        if not user_can_view_inspection(request.user, report.inspection_request):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(
            {"url": report.report_document.url if report.report_document else ""},
            headers={"Cache-Control": "no-store, private"},
        )


class InspectionEvidenceViewSet(mixins.DestroyModelMixin, viewsets.GenericViewSet):
    serializer_class = InspectionEvidenceSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope_by_action = {"signed_url": "inspection_signed_url"}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return InspectionEvidence.objects.none()
        queryset = InspectionEvidence.objects.select_related(
            "inspection_report", "inspection_report__inspection_request", "uploaded_by"
        )
        if user_is_admin(self.request.user):
            return queryset
        return queryset.filter(
            Q(uploaded_by=self.request.user)
            | Q(inspection_report__inspection_request__requester=self.request.user)
            | Q(inspection_report__inspection_request__property__owner=self.request.user)
        ).distinct()

    def destroy(self, request, *args, **kwargs):
        evidence = self.get_object()
        if evidence.uploaded_by_id != request.user.id and not user_is_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
        evidence.delete()
        emit_inspection_event(
            actor=request.user, action="inspection_evidence.deleted", entity=evidence
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="signed-url")
    def signed_url(self, request, pk=None):
        evidence = self.get_object()
        if not user_can_view_evidence(request.user, evidence):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response({"url": evidence.file.url}, headers={"Cache-Control": "no-store, private"})


class AdminInspectionReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InspectionReportSerializer
    permission_classes = [IsAuthenticated, IsInspectionAdmin]

    def get_queryset(self):
        queryset = InspectionReport.objects.select_related(
            "inspection_request", "inspection_request__property", "inspector", "reviewed_by"
        ).prefetch_related("evidence")
        status_value = self.request.query_params.get("status")
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset.order_by("-created_at")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        report = self.get_object()
        report.approve(reviewer=request.user)
        inspection = report.inspection_request
        if inspection.status in [
            InspectionRequestStatus.REPORT_SUBMITTED,
            InspectionRequestStatus.REPORT_UNDER_REVIEW,
        ]:
            inspection.transition_to(InspectionRequestStatus.COMPLETED)
        emit_inspection_event(
            actor=request.user, action="inspection_report.approved", entity=report
        )
        create_timeline_event(
            inspection_request=inspection,
            event_type="InspectionCompleted",
            actor=request.user,
            description="Inspection completed.",
        )
        return Response(self.get_serializer(report).data)

    @action(detail=True, methods=["post"], url_path="request-revision")
    def request_revision(self, request, pk=None):
        report = self.get_object()
        serializer = AdminReportDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "").strip()
        if not reason:
            return Response({"reason": ["Revision reason is required."]}, status=400)
        report.request_revision(reviewer=request.user, reason=reason)
        emit_inspection_event(
            actor=request.user, action="inspection_report.revision_requested", entity=report
        )
        create_timeline_event(
            inspection_request=report.inspection_request,
            event_type="InspectionRevisionRequested",
            actor=request.user,
            description="Inspection report revision requested.",
        )
        return Response(self.get_serializer(report).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        report = self.get_object()
        serializer = AdminReportDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "").strip()
        if not reason:
            return Response({"reason": ["Rejection reason is required."]}, status=400)
        report.reject(reviewer=request.user, reason=reason)
        emit_inspection_event(
            actor=request.user, action="inspection_report.rejected", entity=report
        )
        return Response(self.get_serializer(report).data)


class CustomerInspectionDashboardView(APIView):
    serializer_class = InspectionDashboardSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = InspectionRequest.objects.filter(requester=request.user).select_related(
            "property", "requester", "assigned_inspector"
        )
        stats = [{"label": "My inspections", "value": str(queryset.count())}]
        data = {"stats": stats, "recent_requests": queryset.order_by("-created_at")[:6]}
        return Response(InspectionDashboardSerializer(data, context={"request": request}).data)


class InspectorDashboardView(APIView):
    serializer_class = InspectionDashboardSerializer
    permission_classes = [IsAuthenticated, IsInspector]

    def get(self, request):
        requests = InspectionRequest.objects.filter(assigned_inspector=request.user).select_related(
            "property", "requester", "assigned_inspector"
        )
        assignments = InspectionAssignment.objects.filter(
            inspector=request.user,
            status__in=[AssignmentStatus.ASSIGNED, AssignmentStatus.ACCEPTED],
        ).select_related(
            "inspection_request", "inspection_request__property", "inspector", "assigned_by"
        )
        stats = [{"label": "Assigned inspections", "value": str(requests.count())}]
        data = {
            "stats": stats,
            "recent_requests": requests.order_by("-created_at")[:6],
            "pending_assignments": assignments[:6],
        }
        return Response(InspectionDashboardSerializer(data, context={"request": request}).data)


class AdminInspectionDashboardView(APIView):
    serializer_class = InspectionDashboardSerializer
    permission_classes = [IsAuthenticated, IsInspectionAdmin]

    def get(self, request):
        requests = InspectionRequest.objects.select_related(
            "property", "requester", "assigned_inspector"
        ).order_by("-created_at")
        stats = [
            {"label": item["status"], "value": str(item["total"])}
            for item in InspectionRequest.objects.values("status").annotate(total=Count("id"))
        ]
        data = {
            "stats": stats,
            "recent_requests": requests[:6],
            "pending_walkthroughs": PropertyWalkthrough.objects.filter(
                status=WalkthroughStatus.PENDING_REVIEW
            ).select_related("property", "uploaded_by")[:6],
            "pending_reports": InspectionReport.objects.filter(
                status=InspectionReportStatus.SUBMITTED
            ).select_related("inspection_request", "inspector")[:6],
        }
        return Response(InspectionDashboardSerializer(data, context={"request": request}).data)
