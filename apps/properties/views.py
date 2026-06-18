from __future__ import annotations

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsAdmin
from apps.accounts.services import create_audit_log, user_is_admin
from apps.properties.choices import PropertyStatus
from apps.properties.filters import PublicPropertyFilter
from apps.properties.models import Property
from apps.properties.permissions import IsOwnerOrAdmin
from apps.properties.serializers import (
    PropertyReviewDecisionSerializer,
    PropertySerializer,
    PublicPropertySerializer,
)


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
        queryset = Property.objects.select_related("owner")
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
        return Property.objects.filter(status=PropertyStatus.APPROVED).select_related("owner")

    @extend_schema(
        responses={
            200: PublicPropertySerializer,
            404: OpenApiResponse(description="Property not found"),
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
