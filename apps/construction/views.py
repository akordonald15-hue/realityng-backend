from __future__ import annotations

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from apps.accounts.services import user_is_admin
from apps.construction.choices import (
    ConstructionMilestoneStatus,
    ConstructionProgressUpdateStatus,
    ConstructionProjectStatus,
    ProjectStakeholderStatus,
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
from apps.construction.permissions import IsConstructionAdmin
from apps.construction.serializers import (
    ConstructionDashboardSerializer,
    ConstructionEvidenceSerializer,
    ConstructionMilestoneInspectionSerializer,
    ConstructionMilestoneProgressSerializer,
    ConstructionMilestoneSerializer,
    ConstructionProgressUpdateSerializer,
    ConstructionProjectSerializer,
    ConstructionTimelineEventSerializer,
    MilestoneInspectionRequestSerializer,
    ProgressDecisionSerializer,
    ProjectStakeholderSerializer,
    ProjectStatusTransitionSerializer,
)
from apps.construction.services import (
    apply_approved_progress_update,
    create_project_timeline_event,
    emit_construction_event,
    user_can_create_project_for_property,
    user_can_manage_project,
    user_can_submit_project_update,
    user_can_view_evidence,
    user_can_view_project,
)
from apps.inspections.models import InspectionRequest
from apps.properties.models import Property


class ActionScopedThrottleMixin:
    throttle_scope_by_action: dict[str, str] = {}
    throttle_classes = [AnonRateThrottle, UserRateThrottle, ScopedRateThrottle]

    def get_throttles(self):
        if getattr(self, "action", None) in self.throttle_scope_by_action:
            self.throttle_scope = self.throttle_scope_by_action[self.action]
        return super().get_throttles()


def project_queryset():
    return (
        ConstructionProject.objects.select_related(
            "property",
            "owner",
            "created_by",
            "project_manager",
            "current_milestone",
        )
        .prefetch_related("milestones", "stakeholders__user")
        .annotate(milestone_count=Count("milestones"))
    )


class ConstructionProjectViewSet(ActionScopedThrottleMixin, viewsets.ModelViewSet):
    serializer_class = ConstructionProjectSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"
    filterset_fields = ["status", "project_type", "property", "owner", "project_manager"]
    search_fields = ["name", "description", "contractor_name_or_reference", "property__title"]
    ordering_fields = ["created_at", "planned_end_date", "overall_progress", "name"]
    ordering = ["-created_at"]
    throttle_scope_by_action = {"create": "construction_project_create"}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ConstructionProject.objects.none()
        user = self.request.user
        queryset = project_queryset()
        if user_is_admin(user):
            return queryset
        return queryset.filter(
            Q(owner=user)
            | Q(created_by=user)
            | Q(project_manager=user)
            | Q(stakeholders__user=user, stakeholders__status=ProjectStakeholderStatus.ACTIVE)
            | Q(
                property__assignments__user=user,
                property__assignments__status="active",
            )
        ).distinct()

    def perform_create(self, serializer):
        prop = get_object_or_404(Property, id=serializer.validated_data.pop("property_id"))
        project_manager_id = serializer.validated_data.pop("project_manager_id", None)
        if not user_can_create_project_for_property(self.request.user, prop):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You cannot create construction projects for this property.")
        project = serializer.save(
            property=prop,
            owner=prop.owner,
            created_by=self.request.user,
            project_manager_id=project_manager_id,
        )
        emit_construction_event(
            actor=self.request.user,
            action="construction_project.created",
            entity=project,
            metadata={"property_id": str(prop.id)},
        )
        create_project_timeline_event(
            project=project,
            event_type="ConstructionProjectCreated",
            actor=self.request.user,
            description="Construction project created.",
        )

    def update(self, request, *args, **kwargs):
        project = self.get_object()
        if not user_can_manage_project(request.user, project):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        project = self.get_object()
        if not user_can_manage_project(request.user, project):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        request=ProjectStatusTransitionSerializer, responses={200: ConstructionProjectSerializer}
    )
    @action(detail=True, methods=["post"], url_path="transition")
    def transition(self, request, slug=None):
        project = self.get_object()
        if not user_can_manage_project(request.user, project):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = ProjectStatusTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        next_status = serializer.validated_data["status"]
        try:
            project.transition_to(next_status)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        emit_construction_event(
            actor=request.user,
            action="construction_project.transitioned",
            entity=project,
            metadata={
                "status": project.status,
                "reason": serializer.validated_data.get("reason", ""),
            },
        )
        create_project_timeline_event(
            project=project,
            event_type="ConstructionProjectTransitioned",
            actor=request.user,
            description=f"Project moved to {project.status}.",
            metadata={"reason": serializer.validated_data.get("reason", "")},
        )
        return Response(self.get_serializer(project).data)

    @extend_schema(responses={200: ConstructionTimelineEventSerializer(many=True)})
    @action(detail=True, methods=["get"], url_path="timeline")
    def timeline(self, request, slug=None):
        project = self.get_object()
        events = project.timeline_events.filter(is_internal=False)
        return Response(ConstructionTimelineEventSerializer(events, many=True).data)


class ProjectNestedMixin:
    permission_classes = [IsAuthenticated]

    def get_project(self):
        return get_object_or_404(project_queryset(), slug=self.kwargs["project_slug"])

    def ensure_can_view(self, request, project):
        if not user_can_view_project(request.user, project):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return None

    def ensure_can_manage(self, request, project):
        if not user_can_manage_project(request.user, project):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return None


class ProjectStakeholderViewSet(ProjectNestedMixin, viewsets.ModelViewSet):
    serializer_class = ProjectStakeholderSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or "project_slug" not in self.kwargs:
            return ProjectStakeholder.objects.none()
        project = self.get_project()
        return project.stakeholders.select_related("user", "invited_by")

    def list(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_view(request, project):
            return response
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_view(request, project):
            return response
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_manage(request, project):
            return response
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stakeholder = serializer.save(project=project, invited_by=request.user)
        emit_construction_event(
            actor=request.user,
            action="construction_stakeholder.invited",
            entity=stakeholder,
            metadata={"project_id": str(project.id), "role": stakeholder.stakeholder_role},
        )
        return Response(self.get_serializer(stakeholder).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_manage(request, project):
            return response
        return super().partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_manage(request, project):
            return response
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_manage(request, project):
            return response
        stakeholder = self.get_object()
        stakeholder.revoke()
        emit_construction_event(
            actor=request.user,
            action="construction_stakeholder.revoked",
            entity=stakeholder,
            metadata={"project_id": str(project.id)},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def accept(self, request, project_slug=None, pk=None):
        stakeholder = self.get_object()
        if stakeholder.user_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        stakeholder.accept()
        emit_construction_event(
            actor=request.user,
            action="construction_stakeholder.accepted",
            entity=stakeholder,
        )
        return Response(self.get_serializer(stakeholder).data)


class ConstructionMilestoneViewSet(ProjectNestedMixin, viewsets.ModelViewSet):
    serializer_class = ConstructionMilestoneSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or "project_slug" not in self.kwargs:
            return ConstructionMilestone.objects.none()
        project = self.get_project()
        return project.milestones.annotate(inspection_count=Count("inspection_links"))

    def list(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_view(request, project):
            return response
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_view(request, project):
            return response
        return super().retrieve(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_manage(request, project):
            return response
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        milestone = serializer.save(project=project)
        emit_construction_event(
            actor=request.user,
            action="construction_milestone.created",
            entity=milestone,
            metadata={"project_id": str(project.id)},
        )
        return Response(self.get_serializer(milestone).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_manage(request, project):
            return response
        return super().partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_manage(request, project):
            return response
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_manage(request, project):
            return response
        milestone = self.get_object()
        emit_construction_event(
            actor=request.user,
            action="construction_milestone.deleted",
            entity=milestone,
            metadata={"project_id": str(project.id)},
        )
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        request=ConstructionMilestoneProgressSerializer,
        responses={200: ConstructionMilestoneSerializer},
    )
    @action(detail=True, methods=["post"], url_path="progress")
    def progress(self, request, project_slug=None, pk=None):
        milestone = self.get_object()
        if response := self.ensure_can_manage(request, milestone.project):
            return response
        serializer = ConstructionMilestoneProgressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        previous_progress = milestone.progress_percent
        next_progress = serializer.validated_data.get("progress_percent", previous_progress)
        if next_progress < previous_progress and not serializer.validated_data.get(
            "correction_reason"
        ):
            return Response(
                {"correction_reason": ["Progress reductions require a correction reason."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        milestone.progress_percent = next_progress
        milestone.status = serializer.validated_data.get("status", milestone.status)
        if next_progress == 100:
            milestone.mark_completed_if_allowed()
        else:
            milestone.save(update_fields=["progress_percent", "status", "updated_at"])
        emit_construction_event(
            actor=request.user,
            action="construction_milestone.progress_updated",
            entity=milestone,
            metadata={"previous": str(previous_progress), "current": str(next_progress)},
        )
        return Response(self.get_serializer(milestone).data)

    @extend_schema(
        request=MilestoneInspectionRequestSerializer,
        responses={201: ConstructionMilestoneInspectionSerializer},
    )
    @action(detail=True, methods=["post"], url_path="request-inspection")
    def request_inspection(self, request, project_slug=None, pk=None):
        milestone = self.get_object()
        if response := self.ensure_can_manage(request, milestone.project):
            return response
        serializer = MilestoneInspectionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        inspection = InspectionRequest.objects.create(
            property=milestone.project.property,
            requester=request.user,
            inspection_type=data.get("inspection_type", "construction_progress"),
            purpose=data["purpose"],
            description=data.get("description", ""),
            preferred_date=data.get("preferred_date"),
            alternative_date=data.get("alternative_date"),
            contact_phone=data["contact_phone"],
            contact_email=data["contact_email"],
            access_notes=data.get("access_notes", ""),
            priority=data.get("priority", "normal"),
        )
        link = ConstructionMilestoneInspection.objects.create(
            milestone=milestone,
            inspection_request=inspection,
            requested_by=request.user,
        )
        milestone.status = ConstructionMilestoneStatus.AWAITING_INSPECTION
        milestone.save(update_fields=["status", "updated_at"])
        emit_construction_event(
            actor=request.user,
            action="construction_milestone.inspection_requested",
            entity=link,
            metadata={"inspection_request_id": str(inspection.id)},
        )
        return Response(
            ConstructionMilestoneInspectionSerializer(link, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ConstructionProgressUpdateViewSet(ProjectNestedMixin, viewsets.ModelViewSet):
    serializer_class = ConstructionProgressUpdateSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or "project_slug" not in self.kwargs:
            return ConstructionProgressUpdate.objects.none()
        project = self.get_project()
        return project.progress_updates.select_related("submitted_by", "reviewed_by", "milestone")

    def list(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_view(request, project):
            return response
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_view(request, project):
            return response
        return super().retrieve(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        update = self.get_object()
        if update.status != ConstructionProgressUpdateStatus.DRAFT:
            return Response(
                {"detail": "Only draft progress updates can be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if update.submitted_by_id != request.user.id and not user_can_manage_project(
            request.user,
            update.project,
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        update = self.get_object()
        if update.status != ConstructionProgressUpdateStatus.DRAFT:
            return Response(
                {"detail": "Only draft progress updates can be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if update.submitted_by_id != request.user.id and not user_can_manage_project(
            request.user,
            update.project,
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        emit_construction_event(
            actor=request.user, action="construction_progress_update.deleted", entity=update
        )
        return super().destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        project = self.get_project()
        if not user_can_submit_project_update(request.user, project):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(
            data=request.data, context={"request": request, "project": project}
        )
        serializer.is_valid(raise_exception=True)
        update = serializer.save(project=project, submitted_by=request.user)
        emit_construction_event(
            actor=request.user,
            action="construction_progress_update.created",
            entity=update,
            metadata={"project_id": str(project.id)},
        )
        return Response(self.get_serializer(update).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def submit(self, request, project_slug=None, pk=None):
        update = self.get_object()
        if update.submitted_by_id != request.user.id and not user_can_manage_project(
            request.user, update.project
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        update.submit()
        emit_construction_event(
            actor=request.user, action="construction_progress_update.submitted", entity=update
        )
        return Response(self.get_serializer(update).data)

    @extend_schema(
        request=ProgressDecisionSerializer, responses={200: ConstructionProgressUpdateSerializer}
    )
    @action(detail=True, methods=["post"])
    def approve(self, request, project_slug=None, pk=None):
        update = self.get_object()
        if not user_can_manage_project(request.user, update.project):
            return Response(status=status.HTTP_403_FORBIDDEN)
        update.approve(reviewer=request.user)
        apply_approved_progress_update(update)
        emit_construction_event(
            actor=request.user, action="construction_progress_update.approved", entity=update
        )
        return Response(self.get_serializer(update).data)

    @extend_schema(
        request=ProgressDecisionSerializer, responses={200: ConstructionProgressUpdateSerializer}
    )
    @action(detail=True, methods=["post"])
    def reject(self, request, project_slug=None, pk=None):
        update = self.get_object()
        if not user_can_manage_project(request.user, update.project):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = ProgressDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "").strip()
        if not reason:
            return Response({"reason": ["Rejection reason is required."]}, status=400)
        update.status = ConstructionProgressUpdateStatus.REJECTED
        update.reviewed_by = request.user
        update.reviewed_at = timezone.now()
        update.rejection_reason = reason
        update.save(
            update_fields=["status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"]
        )
        emit_construction_event(
            actor=request.user, action="construction_progress_update.rejected", entity=update
        )
        return Response(self.get_serializer(update).data)


class ConstructionEvidenceViewSet(
    ActionScopedThrottleMixin,
    ProjectNestedMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ConstructionEvidenceSerializer
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope_by_action = {
        "create": "construction_evidence_upload",
        "signed_url": "construction_signed_url",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or "project_slug" not in self.kwargs:
            return ConstructionEvidence.objects.none()
        project = self.get_project()
        return project.evidence.select_related(
            "project", "milestone", "progress_update", "uploaded_by"
        )

    def list(self, request, *args, **kwargs):
        project = self.get_project()
        if response := self.ensure_can_view(request, project):
            return response
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        evidence = self.get_object()
        if not user_can_view_evidence(request.user, evidence):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(self.get_serializer(evidence).data)

    def create(self, request, *args, **kwargs):
        project = self.get_project()
        if not user_can_submit_project_update(request.user, project):
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(
            data=request.data, context={"request": request, "project": project}
        )
        serializer.is_valid(raise_exception=True)
        evidence = serializer.save()
        emit_construction_event(
            actor=request.user,
            action="construction_evidence.uploaded",
            entity=evidence,
            metadata={"project_id": str(project.id), "evidence_type": evidence.evidence_type},
        )
        return Response(self.get_serializer(evidence).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        evidence = self.get_object()
        if evidence.uploaded_by_id != request.user.id and not user_can_manage_project(
            request.user, evidence.project
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        evidence.delete()
        emit_construction_event(
            actor=request.user, action="construction_evidence.deleted", entity=evidence
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"], url_path="signed-url")
    def signed_url(self, request, project_slug=None, pk=None):
        evidence = self.get_object()
        if not user_can_view_evidence(request.user, evidence):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response({"url": evidence.file.url}, headers={"Cache-Control": "no-store, private"})


class ConstructionDashboardBase(APIView):
    permission_classes = [IsAuthenticated]

    def serialize(self, projects, pending_updates=None):
        now = timezone.localdate()
        delayed_projects = projects.filter(
            planned_end_date__lt=now,
        ).exclude(
            status__in=[
                ConstructionProjectStatus.COMPLETED,
                ConstructionProjectStatus.CANCELLED,
                ConstructionProjectStatus.ARCHIVED,
            ]
        )[:5]
        payload = {
            "stats": [
                {"label": "Projects", "value": str(projects.count())},
                {
                    "label": "Active",
                    "value": str(projects.filter(status=ConstructionProjectStatus.ACTIVE).count()),
                },
                {"label": "Delayed", "value": str(delayed_projects.count())},
                {
                    "label": "Pending updates",
                    "value": str(
                        (pending_updates or ConstructionProgressUpdate.objects.none()).count()
                    ),
                },
            ],
            "projects": projects[:8],
            "delayed_projects": delayed_projects,
            "pending_updates": (pending_updates or ConstructionProgressUpdate.objects.none())[:8],
            "activity": ConstructionTimelineEvent.objects.filter(
                project__in=projects, is_internal=False
            ).select_related("actor", "milestone")[:10],
        }
        return Response(ConstructionDashboardSerializer(payload).data)


class OwnerConstructionDashboardView(ConstructionDashboardBase):
    @extend_schema(responses={200: ConstructionDashboardSerializer})
    def get(self, request):
        projects = (
            project_queryset()
            .filter(
                Q(owner=request.user)
                | Q(
                    stakeholders__user=request.user,
                    stakeholders__status=ProjectStakeholderStatus.ACTIVE,
                )
            )
            .distinct()
        )
        updates = ConstructionProgressUpdate.objects.filter(
            project__in=projects, status=ConstructionProgressUpdateStatus.SUBMITTED
        )
        return self.serialize(projects, updates)


class ProjectManagerConstructionDashboardView(ConstructionDashboardBase):
    @extend_schema(responses={200: ConstructionDashboardSerializer})
    def get(self, request):
        projects = (
            project_queryset()
            .filter(
                Q(project_manager=request.user)
                | Q(
                    stakeholders__user=request.user,
                    stakeholders__status=ProjectStakeholderStatus.ACTIVE,
                    stakeholders__access_level__in=["operator", "manager", "owner"],
                )
            )
            .distinct()
        )
        updates = ConstructionProgressUpdate.objects.filter(
            project__in=projects, status=ConstructionProgressUpdateStatus.DRAFT
        )
        return self.serialize(projects, updates)


class AdminConstructionDashboardView(ConstructionDashboardBase):
    permission_classes = [IsAuthenticated, IsConstructionAdmin]

    @extend_schema(responses={200: ConstructionDashboardSerializer})
    def get(self, request):
        projects = project_queryset()
        updates = ConstructionProgressUpdate.objects.filter(
            status=ConstructionProgressUpdateStatus.SUBMITTED
        )
        return self.serialize(projects, updates)
