from __future__ import annotations

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import AuditLog
from apps.accounts.permissions import IsAdmin
from apps.accounts.services import create_audit_log, user_is_admin
from apps.properties.choices import (
    InquiryStatus,
    PropertyStatus,
    RentalApplicationStatus,
    ViewingStatus,
)
from apps.properties.filters import PublicPropertyFilter
from apps.properties.models import (
    Favorite,
    Inquiry,
    Property,
    PropertyImage,
    RentalApplication,
    Viewing,
)
from apps.properties.permissions import IsOwnerOrAdmin
from apps.properties.serializers import (
    DashboardActivityItemSerializer,
    DashboardSummarySerializer,
    FavoriteSerializer,
    InquiryNotesSerializer,
    InquiryPropertySummarySerializer,
    InquirySerializer,
    InquiryStatusUpdateSerializer,
    PropertyAssignmentSerializer,
    PropertyImageMetadataSerializer,
    PropertyImageSerializer,
    PropertyReviewDecisionSerializer,
    PropertySerializer,
    PublicPropertySerializer,
    RentalApplicationNotesSerializer,
    RentalApplicationSerializer,
    RentalApplicationStatusUpdateSerializer,
    TransactionItemSerializer,
    ViewingDecisionSerializer,
    ViewingNotesSerializer,
    ViewingSerializer,
)
from apps.properties.services import (
    emit_application_event,
    emit_inquiry_event,
    emit_property_assignment_event,
    emit_viewing_event,
)


class ActionScopedThrottleMixin:
    throttle_scope_by_action: dict[str, str] = {}
    throttle_classes = [AnonRateThrottle, UserRateThrottle, ScopedRateThrottle]

    def get_throttles(self):
        if getattr(self, "action", None) in self.throttle_scope_by_action:
            self.throttle_scope = self.throttle_scope_by_action[self.action]
        return super().get_throttles()


class PropertyViewSet(ActionScopedThrottleMixin, viewsets.ModelViewSet):
    queryset = Property.objects.none()
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    throttle_scope_by_action = {"images": "property_upload"}
    lookup_field = "slug"
    search_fields = ["title"]
    ordering_fields = ["created_at", "price", "title", "status"]
    ordering = ["-created_at"]
    filterset_fields = ["status", "property_type", "listing_type", "city"]

    def get_queryset(self):
        queryset = Property.objects.select_related("owner").prefetch_related("images")
        if user_is_admin(self.request.user):
            return queryset
        return queryset.filter(owner=self.request.user)

    def perform_destroy(self, instance: Property) -> None:
        create_audit_log(
            actor=self.request.user,
            action="property.deleted",
            entity=instance,
        )
        instance.delete()

    @extend_schema(responses={200: PropertySerializer})
    @action(detail=True, methods=["post"], url_path="submit-for-review")
    def submit_for_review(self, request, slug=None):
        prop = self.get_object()
        prop.submit_for_review()
        create_audit_log(
            actor=request.user,
            action="property.submitted",
            entity=prop,
            metadata={"status": prop.status},
        )
        return Response(PropertySerializer(prop, context={"request": request}).data)

    @extend_schema(
        request=PropertyImageSerializer,
        responses={200: PropertyImageMetadataSerializer(many=True), 201: PropertyImageSerializer},
    )
    @action(
        detail=True,
        methods=["get", "post"],
        url_path="images",
        parser_classes=[MultiPartParser, FormParser],
    )
    def images(self, request, slug=None):
        prop = self.get_object()
        if request.method == "GET":
            serializer = PropertyImageMetadataSerializer(
                prop.images.all(),
                many=True,
                context={"request": request},
            )
            return Response(serializer.data)

        serializer = PropertyImageSerializer(
            data=request.data,
            context={"request": request, "property": prop},
        )
        serializer.is_valid(raise_exception=True)
        image = serializer.save()
        create_audit_log(
            actor=request.user,
            action="property.image_uploaded",
            entity=prop,
            metadata={"image_id": str(image.id), "is_cover": image.is_cover},
        )
        return Response(
            PropertyImageSerializer(image, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=PropertyImageMetadataSerializer,
        parameters=[
            OpenApiParameter("image_id", OpenApiTypes.UUID, OpenApiParameter.PATH),
        ],
        responses={200: PropertyImageMetadataSerializer, 204: None},
    )
    @action(detail=True, methods=["patch", "delete"], url_path=r"images/(?P<image_id>[^/.]+)")
    def image_detail(self, request, slug=None, image_id=None):
        prop = self.get_object()
        image = self._get_property_image(prop, image_id)
        if request.method == "DELETE":
            image_file = image.image
            image.delete()
            image_file.delete(save=False)
            create_audit_log(
                actor=request.user,
                action="property.image_deleted",
                entity=prop,
                metadata={"image_id": str(image_id)},
            )
            if not prop.images.filter(is_cover=True).exists():
                replacement = prop.images.order_by("display_order", "created_at").first()
                if replacement:
                    replacement.set_as_cover()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = PropertyImageMetadataSerializer(
            image,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        create_audit_log(
            actor=request.user,
            action="property.image_updated",
            entity=prop,
            metadata={"image_id": str(image.id)},
        )
        return Response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter("image_id", OpenApiTypes.UUID, OpenApiParameter.PATH),
        ],
        responses={200: PropertyImageMetadataSerializer},
    )
    @action(detail=True, methods=["post"], url_path=r"images/(?P<image_id>[^/.]+)/set-cover")
    def set_cover_image(self, request, slug=None, image_id=None):
        prop = self.get_object()
        image = self._get_property_image(prop, image_id)
        image.set_as_cover()
        create_audit_log(
            actor=request.user,
            action="property.image_cover_set",
            entity=prop,
            metadata={"image_id": str(image.id)},
        )
        return Response(PropertyImageMetadataSerializer(image, context={"request": request}).data)

    def _get_property_image(self, prop: Property, image_id: str | None) -> PropertyImage:
        return get_object_or_404(prop.images.all(), id=image_id)

    @extend_schema(
        request=PropertyAssignmentSerializer,
        responses={200: PropertyAssignmentSerializer(many=True), 201: PropertyAssignmentSerializer},
    )
    @action(detail=True, methods=["get", "post"], url_path="assignments")
    def assignments(self, request, slug=None):
        prop = self.get_object()
        if not (user_is_admin(request.user) or prop.owner_id == request.user.id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        if request.method == "GET":
            queryset = prop.assignments.select_related("user", "assigned_by")
            return Response(
                PropertyAssignmentSerializer(queryset, many=True, context={"request": request}).data
            )
        serializer = PropertyAssignmentSerializer(
            data=request.data,
            context={"request": request, "property": prop},
        )
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save(property=prop, assigned_by=request.user)
        emit_property_assignment_event(
            actor=request.user,
            assignment=assignment,
            event_name="property_assignment.created",
        )
        return Response(
            PropertyAssignmentSerializer(assignment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=PropertyAssignmentSerializer,
        parameters=[OpenApiParameter("assignment_id", OpenApiTypes.UUID, OpenApiParameter.PATH)],
        responses={200: PropertyAssignmentSerializer, 204: None},
    )
    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"assignments/(?P<assignment_id>[^/.]+)",
    )
    def assignment_detail(self, request, slug=None, assignment_id=None):
        prop = self.get_object()
        if not (user_is_admin(request.user) or prop.owner_id == request.user.id):
            return Response(status=status.HTTP_403_FORBIDDEN)
        assignment = get_object_or_404(
            prop.assignments.select_related("user", "assigned_by"), id=assignment_id
        )
        if request.method == "DELETE":
            assignment.revoke()
            emit_property_assignment_event(
                actor=request.user,
                assignment=assignment,
                event_name="property_assignment.revoked",
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = PropertyAssignmentSerializer(
            assignment,
            data=request.data,
            partial=True,
            context={"request": request, "property": prop},
        )
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()
        emit_property_assignment_event(
            actor=request.user,
            assignment=assignment,
            event_name="property_assignment.updated",
        )
        return Response(serializer.data)

    @extend_schema(
        request=PropertyReviewDecisionSerializer,
        responses={200: PropertySerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
        permission_classes=[IsAuthenticated, IsAdmin],
    )
    def approve(self, request, slug=None):
        prop = self.get_object()
        serializer = PropertyReviewDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prop.approve()
        create_audit_log(
            actor=request.user,
            action="property.approved",
            entity=prop,
            metadata={"reason": serializer.validated_data.get("reason", "")},
        )
        return Response(PropertySerializer(prop, context={"request": request}).data)

    @extend_schema(
        request=PropertyReviewDecisionSerializer,
        responses={200: PropertySerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="reject",
        permission_classes=[IsAuthenticated, IsAdmin],
    )
    def reject(self, request, slug=None):
        prop = self.get_object()
        serializer = PropertyReviewDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prop.reject()
        create_audit_log(
            actor=request.user,
            action="property.rejected",
            entity=prop,
            metadata={"reason": serializer.validated_data.get("reason", "")},
        )
        return Response(PropertySerializer(prop, context={"request": request}).data)


class PublicPropertyViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PublicPropertySerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    filterset_class = PublicPropertyFilter
    search_fields = ["title", "city", "lga", "neighborhood", "landmark"]
    ordering_fields = ["created_at", "price", "title", "featured"]
    ordering = ["-featured", "-created_at"]

    def get_queryset(self):
        return (
            Property.objects.filter(status=PropertyStatus.APPROVED)
            .select_related("owner")
            .annotate(image_count_value=Count("images"))
            .prefetch_related("images")
        )

    def get_serializer_context(self) -> dict:
        context = super().get_serializer_context()
        user = self.request.user
        if user.is_authenticated:
            context["favorite_property_ids"] = set(
                Favorite.objects.filter(
                    user=user,
                    property__deleted_at__isnull=True,
                ).values_list("property_id", flat=True)
            )
        return context

    @extend_schema(
        responses={
            200: PublicPropertySerializer,
            404: OpenApiResponse(description="Property not found"),
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class FavoriteViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Favorite.objects.none()
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "property_id"
    lookup_url_kwarg = "property_id"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Favorite.objects.none()
        return (
            Favorite.objects.filter(
                user=self.request.user,
                property__deleted_at__isnull=True,
            )
            .select_related("property", "property__owner")
            .prefetch_related("property__images")
        )

    @extend_schema(
        request=FavoriteSerializer,
        responses={201: FavoriteSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        favorite = serializer.save()
        create_audit_log(
            actor=request.user,
            action="property_favorited",
            entity=favorite.property,
            metadata={"favorite_id": str(favorite.id)},
        )
        headers = self.get_success_headers(serializer.data)
        return Response(
            FavoriteSerializer(favorite, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @extend_schema(
        parameters=[
            OpenApiParameter("property_id", OpenApiTypes.UUID, OpenApiParameter.PATH),
        ],
        responses={204: None},
    )
    def destroy(self, request, *args, **kwargs):
        favorite = self.get_object()
        prop = favorite.property
        favorite_id = favorite.id
        favorite.delete()
        create_audit_log(
            actor=request.user,
            action="property_unfavorited",
            entity=prop,
            metadata={"favorite_id": str(favorite_id)},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class InquiryViewSet(
    ActionScopedThrottleMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Inquiry.objects.none()
    serializer_class = InquirySerializer
    permission_classes = [IsAuthenticated]
    throttle_scope_by_action = {"create": "inquiry_create"}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Inquiry.objects.none()

        user = self.request.user
        queryset = (
            Inquiry.objects.select_related("property", "property__owner", "interested_user")
            .prefetch_related("property__images")
            .filter(property__deleted_at__isnull=True)
        )
        if user_is_admin(user):
            return queryset
        if self.action == "received":
            return queryset.filter(property_owner=user)
        return queryset.filter(Q(interested_user=user) | Q(property_owner=user))

    @extend_schema(request=InquirySerializer, responses={201: InquirySerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inquiry = serializer.save()
        emit_inquiry_event(
            actor=request.user,
            inquiry=inquiry,
            event_name="inquiry.created",
            metadata={"notification_event": "InquiryCreated"},
        )
        headers = self.get_success_headers(serializer.data)
        return Response(
            InquirySerializer(inquiry, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @extend_schema(responses={200: InquirySerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="received")
    def received(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(request=InquiryStatusUpdateSerializer, responses={200: InquirySerializer})
    @action(detail=True, methods=["post"], url_path="status")
    def update_status(self, request, pk=None):
        inquiry = self.get_object()
        if not self._can_manage_inquiry(request.user, inquiry):
            return Response(
                {"detail": "Only the property owner can update inquiry status."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = InquiryStatusUpdateSerializer(
            data=request.data,
            context={"inquiry": inquiry},
        )
        serializer.is_valid(raise_exception=True)
        previous_status = inquiry.status
        next_status = serializer.validated_data["status"]
        inquiry.transition_to(next_status)

        event_name = (
            "inquiry.closed" if next_status == InquiryStatus.CLOSED else "inquiry.status_changed"
        )
        emit_inquiry_event(
            actor=request.user,
            inquiry=inquiry,
            event_name=event_name,
            metadata={
                "notification_event": "InquiryStatusChanged",
                "previous_status": previous_status,
                "next_status": next_status,
            },
        )
        return Response(InquirySerializer(inquiry, context=self.get_serializer_context()).data)

    @extend_schema(request=InquiryNotesSerializer, responses={200: InquirySerializer})
    @action(detail=True, methods=["patch"], url_path="notes")
    def update_notes(self, request, pk=None):
        inquiry = self.get_object()
        if not self._can_manage_inquiry(request.user, inquiry):
            return Response(
                {"detail": "Only the property owner can update internal notes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = InquiryNotesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inquiry.internal_notes = serializer.validated_data["internal_notes"]
        inquiry.save(update_fields=["internal_notes", "updated_at"])
        emit_inquiry_event(
            actor=request.user,
            inquiry=inquiry,
            event_name="inquiry.updated",
            metadata={"notification_event": "InquiryUpdated", "field": "internal_notes"},
        )
        return Response(InquirySerializer(inquiry, context=self.get_serializer_context()).data)

    def _can_manage_inquiry(self, user, inquiry: Inquiry) -> bool:
        return user_is_admin(user) or inquiry.property_owner_id == user.id


class ViewingViewSet(
    ActionScopedThrottleMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Viewing.objects.none()
    serializer_class = ViewingSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope_by_action = {"create": "viewing_create"}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Viewing.objects.none()

        user = self.request.user
        queryset = (
            Viewing.objects.select_related(
                "inquiry",
                "property",
                "property__owner",
                "requester",
                "property_owner",
            )
            .prefetch_related("property__images")
            .filter(property__deleted_at__isnull=True)
        )
        if user_is_admin(user):
            return queryset
        if self.action == "received":
            return queryset.filter(property_owner=user)
        return queryset.filter(Q(requester=user) | Q(property_owner=user))

    @extend_schema(request=ViewingSerializer, responses={201: ViewingSerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        viewing = serializer.save()
        emit_viewing_event(
            actor=request.user,
            viewing=viewing,
            event_name="viewing.created",
            metadata={"notification_event": "ViewingRequested"},
        )
        headers = self.get_success_headers(serializer.data)
        return Response(
            ViewingSerializer(viewing, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @extend_schema(responses={200: ViewingSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="received")
    def received(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(request=ViewingDecisionSerializer, responses={200: ViewingSerializer})
    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        viewing = self.get_object()
        if not self._can_manage_viewing(request.user, viewing):
            return Response(
                {"detail": "Only the property owner can confirm viewing requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ViewingDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self._apply_viewing_decision(
                viewing=viewing,
                payload=serializer.validated_data,
                next_status=ViewingStatus.CONFIRMED,
                actor=request.user,
                event_name="viewing.confirmed",
                notification_event="ViewingConfirmed",
            )
        except ValueError as exc:
            return Response({"status": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ViewingSerializer(viewing, context=self.get_serializer_context()).data)

    @extend_schema(request=ViewingDecisionSerializer, responses={200: ViewingSerializer})
    @action(detail=True, methods=["post"], url_path="reschedule")
    def reschedule(self, request, pk=None):
        viewing = self.get_object()
        if not self._can_manage_viewing(request.user, viewing):
            return Response(
                {"detail": "Only the property owner can reschedule viewing requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ViewingDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self._apply_viewing_decision(
                viewing=viewing,
                payload=serializer.validated_data,
                next_status=ViewingStatus.RESCHEDULED,
                actor=request.user,
                event_name="viewing.rescheduled",
                notification_event="ViewingRescheduled",
            )
        except ValueError as exc:
            return Response({"status": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ViewingSerializer(viewing, context=self.get_serializer_context()).data)

    @extend_schema(request=ViewingNotesSerializer, responses={200: ViewingSerializer})
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        viewing = self.get_object()
        if not self._is_viewing_participant(request.user, viewing):
            return Response(
                {"detail": "Only viewing participants can cancel viewing requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ViewingNotesSerializer(
            data={"notes": request.data.get("notes", viewing.notes)}
        )
        serializer.is_valid(raise_exception=True)
        viewing.notes = serializer.validated_data["notes"]
        try:
            viewing.transition_to(ViewingStatus.CANCELLED)
        except ValueError as exc:
            return Response({"status": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        viewing.save(update_fields=["notes", "updated_at"])
        emit_viewing_event(
            actor=request.user,
            viewing=viewing,
            event_name="viewing.cancelled",
            metadata={"notification_event": "ViewingCancelled"},
        )
        return Response(ViewingSerializer(viewing, context=self.get_serializer_context()).data)

    @extend_schema(responses={200: ViewingSerializer})
    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        viewing = self.get_object()
        if not self._can_manage_viewing(request.user, viewing):
            return Response(
                {"detail": "Only the property owner can complete viewing requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            viewing.transition_to(ViewingStatus.COMPLETED)
        except ValueError as exc:
            return Response({"status": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        emit_viewing_event(
            actor=request.user,
            viewing=viewing,
            event_name="viewing.completed",
            metadata={"notification_event": "ViewingCompleted"},
        )
        return Response(ViewingSerializer(viewing, context=self.get_serializer_context()).data)

    @extend_schema(request=ViewingNotesSerializer, responses={200: ViewingSerializer})
    @action(detail=True, methods=["patch"], url_path="notes")
    def update_notes(self, request, pk=None):
        viewing = self.get_object()
        if not self._is_viewing_participant(request.user, viewing):
            return Response(
                {"detail": "Only viewing participants can update notes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ViewingNotesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        viewing.notes = serializer.validated_data["notes"]
        viewing.save(update_fields=["notes", "updated_at"])
        emit_viewing_event(
            actor=request.user,
            viewing=viewing,
            event_name="viewing.updated",
            metadata={"notification_event": "ViewingUpdated", "field": "notes"},
        )
        return Response(ViewingSerializer(viewing, context=self.get_serializer_context()).data)

    def _apply_viewing_decision(
        self,
        *,
        viewing: Viewing,
        payload: dict,
        next_status: str,
        actor,
        event_name: str,
        notification_event: str,
    ) -> None:
        viewing.confirmed_datetime = payload["confirmed_datetime"]
        viewing.meeting_location = payload.get("meeting_location", viewing.meeting_location)
        viewing.meeting_link = payload.get("meeting_link", viewing.meeting_link)
        viewing.notes = payload.get("notes", viewing.notes)
        try:
            viewing.transition_to(next_status)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        viewing.save(
            update_fields=[
                "confirmed_datetime",
                "meeting_location",
                "meeting_link",
                "notes",
                "updated_at",
            ]
        )
        self._mark_inquiry_viewing_scheduled(viewing.inquiry)
        emit_viewing_event(
            actor=actor,
            viewing=viewing,
            event_name=event_name,
            metadata={
                "notification_event": notification_event,
                "confirmed_datetime": viewing.confirmed_datetime.isoformat(),
            },
        )

    def _mark_inquiry_viewing_scheduled(self, inquiry: Inquiry) -> None:
        if inquiry.status == InquiryStatus.NEW:
            inquiry.transition_to(InquiryStatus.CONTACTED)
        if inquiry.status == InquiryStatus.CONTACTED:
            inquiry.transition_to(InquiryStatus.VIEWING_SCHEDULED)

    def _can_manage_viewing(self, user, viewing: Viewing) -> bool:
        return user_is_admin(user) or viewing.property_owner_id == user.id

    def _is_viewing_participant(self, user, viewing: Viewing) -> bool:
        return (
            user_is_admin(user)
            or viewing.property_owner_id == user.id
            or viewing.requester_id == user.id
        )


class RentalApplicationViewSet(
    ActionScopedThrottleMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = RentalApplication.objects.none()
    serializer_class = RentalApplicationSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope_by_action = {"create": "application_create"}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return RentalApplication.objects.none()

        user = self.request.user
        queryset = (
            RentalApplication.objects.select_related(
                "property",
                "property__owner",
                "applicant",
                "property_owner",
                "inquiry",
                "viewing",
            )
            .prefetch_related("property__images")
            .filter(property__deleted_at__isnull=True)
        )
        if user_is_admin(user):
            return queryset
        if self.action == "received":
            return queryset.filter(property_owner=user)
        return queryset.filter(Q(applicant=user) | Q(property_owner=user))

    @extend_schema(
        request=RentalApplicationSerializer,
        responses={201: RentalApplicationSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        emit_application_event(
            actor=request.user,
            application=application,
            event_name="application.submitted",
            metadata={"notification_event": "ApplicationSubmitted"},
        )
        headers = self.get_success_headers(serializer.data)
        return Response(
            RentalApplicationSerializer(application, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    @extend_schema(responses={200: RentalApplicationSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="received")
    def received(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(responses={200: RentalApplicationSerializer})
    @action(detail=True, methods=["post"], url_path="under-review")
    def mark_under_review(self, request, pk=None):
        application = self.get_object()
        if not self._can_manage_application(request.user, application):
            return Response(
                {"detail": "Only the property owner can review applications."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return self._transition_application(
            request=request,
            application=application,
            next_status=RentalApplicationStatus.UNDER_REVIEW,
            event_name="application.under_review",
            notification_event="ApplicationUnderReview",
        )

    @extend_schema(responses={200: RentalApplicationSerializer})
    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        application = self.get_object()
        if not self._can_manage_application(request.user, application):
            return Response(
                {"detail": "Only the property owner can approve applications."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return self._transition_application(
            request=request,
            application=application,
            next_status=RentalApplicationStatus.APPROVED,
            event_name="application.approved",
            notification_event="ApplicationApproved",
        )

    @extend_schema(responses={200: RentalApplicationSerializer})
    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        application = self.get_object()
        if not self._can_manage_application(request.user, application):
            return Response(
                {"detail": "Only the property owner can reject applications."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return self._transition_application(
            request=request,
            application=application,
            next_status=RentalApplicationStatus.REJECTED,
            event_name="application.rejected",
            notification_event="ApplicationRejected",
        )

    @extend_schema(responses={200: RentalApplicationSerializer})
    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        application = self.get_object()
        if not self._is_application_applicant(request.user, application) and not user_is_admin(
            request.user
        ):
            return Response(
                {"detail": "Only the applicant can withdraw applications."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return self._transition_application(
            request=request,
            application=application,
            next_status=RentalApplicationStatus.WITHDRAWN,
            event_name="application.withdrawn",
            notification_event="ApplicationWithdrawn",
        )

    @extend_schema(
        request=RentalApplicationNotesSerializer,
        responses={200: RentalApplicationSerializer},
    )
    @action(detail=True, methods=["patch"], url_path="notes")
    def update_notes(self, request, pk=None):
        application = self.get_object()
        if not self._can_manage_application(request.user, application):
            return Response(
                {"detail": "Only the property owner can update owner notes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = RentalApplicationNotesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application.owner_notes = serializer.validated_data["owner_notes"]
        application.save(update_fields=["owner_notes", "updated_at"])
        emit_application_event(
            actor=request.user,
            application=application,
            event_name="application.updated",
            metadata={"notification_event": "ApplicationUpdated", "field": "owner_notes"},
        )
        return Response(
            RentalApplicationSerializer(application, context=self.get_serializer_context()).data
        )

    def _transition_application(
        self,
        *,
        request,
        application: RentalApplication,
        next_status: str,
        event_name: str,
        notification_event: str,
    ) -> Response:
        previous_status = application.status
        serializer = RentalApplicationStatusUpdateSerializer(
            data={"status": next_status},
            context={"application": application},
        )
        serializer.is_valid(raise_exception=True)
        try:
            application.transition_to(next_status)
        except ValueError as exc:
            return Response({"status": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        emit_application_event(
            actor=request.user,
            application=application,
            event_name=event_name,
            metadata={
                "notification_event": notification_event,
                "previous_status": previous_status,
                "next_status": next_status,
            },
        )
        return Response(
            RentalApplicationSerializer(application, context=self.get_serializer_context()).data
        )

    def _can_manage_application(self, user, application: RentalApplication) -> bool:
        return user_is_admin(user) or application.property_owner_id == user.id

    def _is_application_applicant(self, user, application: RentalApplication) -> bool:
        return application.applicant_id == user.id


ACTIVITY_LABELS = {
    "property_favorited": "Property saved",
    "property_unfavorited": "Property removed from saved list",
    "inquiry.created": "Inquiry submitted",
    "inquiry.status_changed": "Inquiry status updated",
    "inquiry.closed": "Inquiry closed",
    "viewing.created": "Viewing requested",
    "viewing.confirmed": "Viewing confirmed",
    "viewing.rescheduled": "Viewing rescheduled",
    "viewing.cancelled": "Viewing cancelled",
    "viewing.completed": "Viewing completed",
    "application.submitted": "Application submitted",
    "application.under_review": "Application moved under review",
    "application.approved": "Application approved",
    "application.rejected": "Application rejected",
    "application.withdrawn": "Application withdrawn",
}


class DashboardActivityView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: DashboardActivityItemSerializer(many=True)})
    def get(self, request):
        queryset = AuditLog.objects.select_related("actor")
        if not user_is_admin(request.user):
            user_id = str(request.user.id)
            queryset = queryset.filter(
                Q(actor=request.user)
                | Q(metadata__property_owner_id=user_id)
                | Q(metadata__interested_user_id=user_id)
                | Q(metadata__requester_id=user_id)
                | Q(metadata__applicant_id=user_id)
            )
        data = [
            {
                "id": item.id,
                "action": item.action,
                "label": ACTIVITY_LABELS.get(item.action, item.action.replace("_", " ").title()),
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "property_id": item.metadata.get("property_id", ""),
                "occurred_at": item.created_at,
            }
            for item in queryset.order_by("-created_at")[:25]
        ]
        return Response(DashboardActivityItemSerializer(data, many=True).data)


class TransactionCenterView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: TransactionItemSerializer(many=True)})
    def get(self, request):
        user = request.user
        inquiry_queryset = (
            Inquiry.objects.select_related("property", "interested_user", "property_owner")
            .prefetch_related("property__images", "viewings", "rental_applications")
            .filter(property__deleted_at__isnull=True)
        )
        if not user_is_admin(user):
            inquiry_queryset = inquiry_queryset.filter(
                Q(interested_user=user) | Q(property_owner=user)
            )

        data = [
            self._serialize_transaction(request, inquiry)
            for inquiry in inquiry_queryset.order_by("-updated_at")[:25]
        ]
        return Response(TransactionItemSerializer(data, many=True).data)

    def _serialize_transaction(self, request, inquiry: Inquiry) -> dict:
        latest_viewing = max(
            list(inquiry.viewings.all()),
            key=lambda item: item.updated_at,
            default=None,
        )
        latest_application = max(
            list(inquiry.rental_applications.all()),
            key=lambda item: item.updated_at,
            default=None,
        )
        stage, stage_label, next_action, last_update = self._stage_for(
            inquiry,
            latest_viewing,
            latest_application,
        )
        return {
            "property": InquiryPropertySummarySerializer(
                inquiry.property,
                context={"request": request},
            ).data,
            "stage": stage,
            "stage_label": stage_label,
            "last_update": last_update,
            "next_action": next_action,
            "inquiry_id": inquiry.id,
            "viewing_id": latest_viewing.id if latest_viewing else None,
            "application_id": latest_application.id if latest_application else None,
        }

    def _stage_for(
        self,
        inquiry: Inquiry,
        viewing: Viewing | None,
        application: RentalApplication | None,
    ) -> tuple[str, str, str, object]:
        if application:
            labels = {
                RentalApplicationStatus.SUBMITTED: "Application Submitted",
                RentalApplicationStatus.UNDER_REVIEW: "Application Under Review",
                RentalApplicationStatus.APPROVED: "Application Approved",
                RentalApplicationStatus.REJECTED: "Application Rejected",
                RentalApplicationStatus.WITHDRAWN: "Application Withdrawn",
            }
            next_actions = {
                RentalApplicationStatus.SUBMITTED: "Await owner review",
                RentalApplicationStatus.UNDER_REVIEW: "Await owner decision",
                RentalApplicationStatus.APPROVED: "Prepare verification and lease steps",
                RentalApplicationStatus.REJECTED: "Review other properties",
                RentalApplicationStatus.WITHDRAWN: "Apply again when ready",
            }
            return (
                application.status,
                labels[application.status],
                next_actions[application.status],
                application.updated_at,
            )

        if viewing:
            labels = {
                ViewingStatus.REQUESTED: "Viewing Requested",
                ViewingStatus.RESCHEDULED: "Viewing Rescheduled",
                ViewingStatus.CONFIRMED: "Viewing Confirmed",
                ViewingStatus.COMPLETED: "Viewing Completed",
                ViewingStatus.CANCELLED: "Viewing Cancelled",
            }
            next_actions = {
                ViewingStatus.REQUESTED: "Await owner confirmation",
                ViewingStatus.RESCHEDULED: "Confirm new viewing plan",
                ViewingStatus.CONFIRMED: "Attend viewing",
                ViewingStatus.COMPLETED: "Apply for property",
                ViewingStatus.CANCELLED: "Request another viewing",
            }
            return (
                viewing.status,
                labels[viewing.status],
                next_actions[viewing.status],
                viewing.updated_at,
            )

        labels = {
            InquiryStatus.NEW: "Inquiry Submitted",
            InquiryStatus.CONTACTED: "Inquiry Contacted",
            InquiryStatus.VIEWING_SCHEDULED: "Viewing Scheduled",
            InquiryStatus.NEGOTIATING: "Negotiating",
            InquiryStatus.CONVERTED: "Converted",
            InquiryStatus.CLOSED: "Closed",
        }
        next_actions = {
            InquiryStatus.NEW: "Request viewing",
            InquiryStatus.CONTACTED: "Request viewing",
            InquiryStatus.VIEWING_SCHEDULED: "Review viewing details",
            InquiryStatus.NEGOTIATING: "Continue owner follow-up",
            InquiryStatus.CONVERTED: "Transaction converted",
            InquiryStatus.CLOSED: "Browse other properties",
        }
        return (
            inquiry.status,
            labels[inquiry.status],
            next_actions[inquiry.status],
            inquiry.updated_at,
        )


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: DashboardSummarySerializer})
    def get(self, request):
        data = {
            "saved_properties_count": Favorite.objects.filter(
                user=request.user,
                property__deleted_at__isnull=True,
            ).count(),
            "active_listings_count": Property.objects.filter(
                owner=request.user,
                status=PropertyStatus.APPROVED,
            ).count(),
            "draft_listings_count": Property.objects.filter(
                owner=request.user,
                status=PropertyStatus.DRAFT,
            ).count(),
            "my_inquiries_count": Inquiry.objects.filter(
                interested_user=request.user,
                property__deleted_at__isnull=True,
            ).count(),
            "received_inquiries_count": Inquiry.objects.filter(
                property_owner=request.user,
                property__deleted_at__isnull=True,
            ).count(),
            "my_viewings_count": Viewing.objects.filter(
                requester=request.user,
                property__deleted_at__isnull=True,
            ).count(),
            "received_viewings_count": Viewing.objects.filter(
                property_owner=request.user,
                property__deleted_at__isnull=True,
            ).count(),
            "my_applications_count": RentalApplication.objects.filter(
                applicant=request.user,
                property__deleted_at__isnull=True,
            ).count(),
            "received_applications_count": RentalApplication.objects.filter(
                property_owner=request.user,
                property__deleted_at__isnull=True,
            ).count(),
        }
        return Response(DashboardSummarySerializer(data).data)
