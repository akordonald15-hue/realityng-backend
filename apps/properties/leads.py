from __future__ import annotations

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters import rest_framework as filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.services import user_is_admin
from apps.properties.choices import (
    LeadActivityType,
    LeadPipelineStage,
    LeadPriority,
    PropertyAssignmentCapability,
)
from apps.properties.models import Inquiry, LeadActivity
from apps.properties.serializers import (
    InquiryPropertySummarySerializer,
    InquiryUserSerializer,
)
from apps.properties.services import (
    emit_inquiry_event,
    emit_lead_assigned_event,
    emit_lead_reassigned_event,
    property_ids_for_user_capability,
    user_has_property_capability,
)


def _can_manage_lead(user, inquiry: Inquiry) -> bool:
    return (
        user_is_admin(user)
        or inquiry.property_owner_id == user.id
        or user_has_property_capability(
            user,
            inquiry.property,
            PropertyAssignmentCapability.MANAGE_LEADS,
        )
    )


def _can_assign_lead_to(user, inquiry: Inquiry) -> bool:
    if not user:
        return True
    return user_has_property_capability(
        user,
        inquiry.property,
        PropertyAssignmentCapability.MANAGE_LEADS,
    )


class LeadActivitySerializer(serializers.ModelSerializer):
    actor = InquiryUserSerializer(read_only=True)

    class Meta:
        model = LeadActivity
        fields = [
            "id",
            "inquiry",
            "actor",
            "activity_type",
            "note",
            "scheduled_for",
            "completed_at",
            "created_at",
        ]
        read_only_fields = ["id", "inquiry", "actor", "created_at"]


class LeadActivityCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadActivity
        fields = ["activity_type", "note", "scheduled_for", "completed_at"]

    def create(self, validated_data):
        inquiry = self.context["inquiry"]
        request = self.context["request"]
        activity = LeadActivity.objects.create(
            inquiry=inquiry,
            actor=request.user,
            **validated_data,
        )
        update_fields = []
        if activity.activity_type in (
            LeadActivityType.CALL,
            LeadActivityType.WHATSAPP,
            LeadActivityType.EMAIL,
        ):
            inquiry.last_contacted_at = timezone.now()
            update_fields.append("last_contacted_at")
        if activity.activity_type == LeadActivityType.FOLLOW_UP_COMPLETED:
            inquiry.follow_up_count = inquiry.follow_up_count + 1
            update_fields.append("follow_up_count")
        if (
            activity.activity_type == LeadActivityType.FOLLOW_UP_SCHEDULED
            and activity.scheduled_for
        ):
            inquiry.next_follow_up_at = activity.scheduled_for
            update_fields.append("next_follow_up_at")
        if update_fields:
            inquiry.save(update_fields=[*update_fields, "updated_at"])
        emit_inquiry_event(
            actor=request.user,
            inquiry=inquiry,
            event_name="lead_activity_logged",
            metadata={
                "activity_id": str(activity.id),
                "activity_type": activity.activity_type,
                "scheduled_for": (
                    activity.scheduled_for.isoformat() if activity.scheduled_for else None
                ),
            },
        )
        return activity


class LeadSerializer(serializers.ModelSerializer):
    property = InquiryPropertySummarySerializer(read_only=True)
    interested_user = InquiryUserSerializer(read_only=True)
    property_owner = InquiryUserSerializer(read_only=True)
    assigned_to = InquiryUserSerializer(read_only=True)

    class Meta:
        model = Inquiry
        fields = [
            "id",
            "property",
            "interested_user",
            "property_owner",
            "inquiry_type",
            "message",
            "status",
            "pipeline_stage",
            "priority",
            "assigned_to",
            "source",
            "last_contacted_at",
            "next_follow_up_at",
            "follow_up_count",
            "closed_reason",
            "conversion_value",
            "converted_at",
            "internal_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class LeadAssignSerializer(serializers.Serializer):
    assigned_to_id = serializers.UUIDField(allow_null=True)

    def validate_assigned_to_id(self, value):
        if value is None:
            return value
        try:
            assignee = User.objects.get(pk=value)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("Assigned user does not exist.") from exc
        inquiry = self.context["inquiry"]
        if not _can_assign_lead_to(assignee, inquiry):
            raise serializers.ValidationError(
                "Assigned user must have an active lead-management assignment "
                "for this property."
            )
        return value


class LeadPipelineTransitionSerializer(serializers.Serializer):
    pipeline_stage = serializers.ChoiceField(choices=LeadPipelineStage.choices)

    def validate_pipeline_stage(self, value):
        inquiry = self.context["inquiry"]
        if value != inquiry.pipeline_stage and not inquiry.can_transition_pipeline_to(value):
            raise serializers.ValidationError(
                f"Lead cannot move from {inquiry.pipeline_stage} to {value}."
            )
        return value


class LeadFilterSet(filters.FilterSet):
    property = filters.UUIDFilter(field_name="property_id")
    pipeline_stage = filters.ChoiceFilter(choices=LeadPipelineStage.choices)
    priority = filters.ChoiceFilter(choices=LeadPriority.choices)
    assigned_to = filters.UUIDFilter(field_name="assigned_to_id")
    created_after = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")
    next_follow_up_before = filters.IsoDateTimeFilter(
        field_name="next_follow_up_at", lookup_expr="lte"
    )

    class Meta:
        model = Inquiry
        fields = ["property", "pipeline_stage", "priority", "assigned_to"]


class LeadViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Inquiry.objects.none()
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.DjangoFilterBackend, SearchFilter]
    filterset_class = LeadFilterSet
    search_fields = ["interested_user__full_name", "interested_user__email", "property__title"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Inquiry.objects.none()
        user = self.request.user
        queryset = Inquiry.objects.select_related(
            "property", "property_owner", "interested_user", "assigned_to"
        ).filter(property__deleted_at__isnull=True)
        if user_is_admin(user):
            return queryset
        managed_property_ids = property_ids_for_user_capability(
            user,
            PropertyAssignmentCapability.MANAGE_LEADS,
        )
        return queryset.filter(
            Q(property_owner=user)
            | Q(property_id__in=managed_property_ids)
        ).distinct()

    def _get_lead(self, pk):
        return get_object_or_404(self.get_queryset(), pk=pk)

    @extend_schema(request=LeadAssignSerializer, responses={200: LeadSerializer})
    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        inquiry = self._get_lead(pk)
        if not _can_manage_lead(request.user, inquiry):
            return Response(
                {"detail": "Only the property owner or admin can assign leads."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = LeadAssignSerializer(data=request.data, context={"inquiry": inquiry})
        serializer.is_valid(raise_exception=True)
        previous_assigned_to_id = (
            str(inquiry.assigned_to_id) if inquiry.assigned_to_id else None
        )
        inquiry.assigned_to_id = serializer.validated_data["assigned_to_id"]
        inquiry.save(update_fields=["assigned_to", "updated_at"])
        if previous_assigned_to_id:
            emit_lead_reassigned_event(
                actor=request.user,
                inquiry=inquiry,
                previous_assigned_to_id=previous_assigned_to_id,
            )
        else:
            emit_lead_assigned_event(actor=request.user, inquiry=inquiry)
        return Response(LeadSerializer(inquiry).data)

    @extend_schema(request=LeadPipelineTransitionSerializer, responses={200: LeadSerializer})
    @action(detail=True, methods=["post"], url_path="transition")
    def transition(self, request, pk=None):
        inquiry = self._get_lead(pk)
        if not _can_manage_lead(request.user, inquiry):
            return Response(
                {
                    "detail": (
                        "Only the property owner, assigned agent, or admin can "
                        "update lead stage."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = LeadPipelineTransitionSerializer(
            data=request.data, context={"inquiry": inquiry}
        )
        serializer.is_valid(raise_exception=True)
        previous_stage = inquiry.pipeline_stage
        next_stage = serializer.validated_data["pipeline_stage"]
        inquiry.transition_pipeline_to(next_stage)
        emit_inquiry_event(
            actor=request.user,
            inquiry=inquiry,
            event_name="lead_pipeline_changed",
            metadata={
                "previous_stage": previous_stage,
                "next_stage": next_stage,
                "notification_event": "LeadStageChanged",
            },
        )
        return Response(LeadSerializer(inquiry).data)

    @extend_schema(responses={200: LeadActivitySerializer(many=True)})
    @action(detail=True, methods=["get"], url_path="activities")
    def list_activities(self, request, pk=None):
        inquiry = self._get_lead(pk)
        if not _can_manage_lead(request.user, inquiry):
            return Response(
                {
                    "detail": (
                        "Only the property owner, assigned agent, or admin can "
                        "view lead activity."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        queryset = inquiry.activities.select_related("actor")
        serializer = LeadActivitySerializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(request=LeadActivityCreateSerializer, responses={201: LeadActivitySerializer})
    @action(detail=True, methods=["post"], url_path="log-activity")
    def log_activity(self, request, pk=None):
        inquiry = self._get_lead(pk)
        if not _can_manage_lead(request.user, inquiry):
            return Response(
                {
                    "detail": (
                        "Only the property owner, assigned agent, or admin can "
                        "log lead activity."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = LeadActivityCreateSerializer(
            data=request.data,
            context={"inquiry": inquiry, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        activity = serializer.save()
        return Response(LeadActivitySerializer(activity).data, status=status.HTTP_201_CREATED)


class DashboardLeadsSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        user = request.user
        queryset = Inquiry.objects.filter(property__deleted_at__isnull=True)
        if not user_is_admin(user):
            queryset = queryset.filter(Q(property_owner=user) | Q(assigned_to=user))

        total_leads = queryset.count()
        new_leads = queryset.filter(pipeline_stage=LeadPipelineStage.NEW).count()
        contacted_leads = queryset.filter(pipeline_stage=LeadPipelineStage.CONTACTED).count()
        upcoming_follow_ups = queryset.filter(
            next_follow_up_at__isnull=False,
            next_follow_up_at__gte=timezone.now(),
        ).count()
        viewings_or_later = queryset.filter(
            pipeline_stage__in=[
                LeadPipelineStage.VIEWING_SCHEDULED,
                LeadPipelineStage.APPLICATION_STARTED,
                LeadPipelineStage.APPLICATION_SUBMITTED,
                LeadPipelineStage.NEGOTIATING,
                LeadPipelineStage.CONVERTED,
            ]
        ).count()
        applications_or_later = queryset.filter(
            pipeline_stage__in=[
                LeadPipelineStage.APPLICATION_SUBMITTED,
                LeadPipelineStage.NEGOTIATING,
                LeadPipelineStage.CONVERTED,
            ]
        ).count()
        converted_count = queryset.filter(pipeline_stage=LeadPipelineStage.CONVERTED).count()
        closed_lost_count = queryset.filter(pipeline_stage=LeadPipelineStage.CLOSED_LOST).count()

        viewing_conversion_rate = (
            round((viewings_or_later / total_leads) * 100, 1) if total_leads else 0.0
        )
        application_conversion_rate = (
            round((applications_or_later / total_leads) * 100, 1) if total_leads else 0.0
        )

        response_seconds = [
            (inquiry.last_contacted_at - inquiry.created_at).total_seconds()
            for inquiry in queryset.filter(last_contacted_at__isnull=False).only(
                "created_at", "last_contacted_at"
            )
        ]
        average_response_seconds = (
            round(sum(response_seconds) / len(response_seconds), 0)
            if response_seconds
            else None
        )

        return Response(
            {
                "total_leads": total_leads,
                "new_leads": new_leads,
                "contacted_leads": contacted_leads,
                "upcoming_follow_ups": upcoming_follow_ups,
                "viewing_conversion_rate": viewing_conversion_rate,
                "application_conversion_rate": application_conversion_rate,
                "converted_count": converted_count,
                "closed_lost_count": closed_lost_count,
                "average_response_seconds": average_response_seconds,
            }
        )
