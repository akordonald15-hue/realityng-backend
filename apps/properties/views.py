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
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.accounts.services import create_audit_log, user_is_admin
from apps.properties.choices import InquiryStatus, PropertyStatus
from apps.properties.filters import PublicPropertyFilter
from apps.properties.models import Favorite, Inquiry, Property, PropertyImage
from apps.properties.permissions import IsOwnerOrAdmin
from apps.properties.serializers import (
    DashboardSummarySerializer,
    FavoriteSerializer,
    InquiryNotesSerializer,
    InquirySerializer,
    InquiryStatusUpdateSerializer,
    PropertyImageMetadataSerializer,
    PropertyImageSerializer,
    PropertyReviewDecisionSerializer,
    PropertySerializer,
    PublicPropertySerializer,
)
from apps.properties.services import emit_inquiry_event


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.none()
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
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
    search_fields = ["title"]
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
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Inquiry.objects.none()
    serializer_class = InquirySerializer
    permission_classes = [IsAuthenticated]

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
            "inquiry.closed"
            if next_status == InquiryStatus.CLOSED
            else "inquiry.status_changed"
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
        }
        return Response(DashboardSummarySerializer(data).data)
