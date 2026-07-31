from __future__ import annotations

from django.db.models import Prefetch
from rest_framework import viewsets

from apps.accounts.services import user_is_admin
from apps.services.filters import PublicServiceProviderFilter
from apps.services.models import ServiceProvider, TradeCategory
from apps.services.permissions import PublicReadOrAdminOnly
from apps.services.serializers import (
    PublicServiceProviderDetailSerializer,
    PublicServiceProviderListSerializer,
    TradeCategorySerializer,
)


class TradeCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TradeCategorySerializer
    permission_classes = [PublicReadOrAdminOnly]
    lookup_field = "slug"
    pagination_class = None

    def get_queryset(self):
        active_children = TradeCategory.objects.filter(is_active=True).order_by(
            "display_order", "name"
        )
        return (
            TradeCategory.objects.filter(is_active=True, parent__isnull=True)
            .prefetch_related(
                Prefetch("children", queryset=active_children, to_attr="prefetched_children")
            )
            .order_by("display_order", "name")
        )


class PublicServiceProviderViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [PublicReadOrAdminOnly]
    lookup_field = "slug"
    filterset_class = PublicServiceProviderFilter
    search_fields = ["business_name", "headline", "biography", "city", "lga", "neighborhood"]
    ordering_fields = ["created_at", "average_rating", "business_name", "completed_jobs_count"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PublicServiceProviderDetailSerializer
        return PublicServiceProviderListSerializer

    def get_queryset(self):
        queryset = ServiceProvider.objects.select_related("user").prefetch_related(
            "trades__category", "service_areas"
        )
        if user_is_admin(self.request.user):
            return queryset
        return queryset.filter(status="active")
