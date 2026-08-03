from __future__ import annotations

from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services import user_is_admin
from apps.services.choices import ProviderStatus, ProviderTradeStatus
from apps.services.filters import PublicServiceProviderFilter
from apps.services.models import (
    PortfolioImage,
    ProviderTrade,
    ServiceArea,
    ServiceProvider,
    TradeCategory,
)
from apps.services.permissions import (
    IsEligibleServiceProvider,
    IsServiceProviderOwner,
    IsServicesAdmin,
    PublicReadOrAdminOnly,
)
from apps.services.serializers import (
    AdminDecisionSerializer,
    AdminServiceProviderSerializer,
    PortfolioImageMetadataSerializer,
    PortfolioImagePublicSerializer,
    PortfolioImageSerializer,
    PortfolioReorderSerializer,
    ProviderTradeWriteSerializer,
    PublicServiceProviderDetailSerializer,
    PublicServiceProviderListSerializer,
    ServiceAreaWriteSerializer,
    ServiceProviderOwnerSerializer,
    TradeCategorySerializer,
    active_public_provider_queryset,
    validate_provider_submission,
)
from apps.services.services import emit_service_event


def provider_queryset():
    return ServiceProvider.objects.select_related("user", "reviewed_by").prefetch_related(
        "trades__category",
        "service_areas",
        "portfolio_images__category",
    )


def get_current_provider(user) -> ServiceProvider:
    return get_object_or_404(provider_queryset(), user=user)


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
        queryset = provider_queryset()
        if user_is_admin(self.request.user):
            return queryset
        return active_public_provider_queryset()


class ProviderProfileView(APIView):
    serializer_class = ServiceProviderOwnerSerializer
    permission_classes = [IsAuthenticated, IsEligibleServiceProvider]

    @extend_schema(
        request=ServiceProviderOwnerSerializer,
        responses={201: ServiceProviderOwnerSerializer},
    )
    def post(self, request):
        if ServiceProvider.objects.filter(user=request.user).exists():
            return Response(
                {"detail": "You already have a provider profile."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ServiceProviderOwnerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = serializer.save(user=request.user)
        emit_service_event(
            actor=request.user,
            action="service_provider.created",
            entity=provider,
        )
        return Response(
            ServiceProviderOwnerSerializer(provider, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ProviderProfileMeView(APIView):
    serializer_class = ServiceProviderOwnerSerializer
    permission_classes = [IsAuthenticated, IsServiceProviderOwner]

    @extend_schema(responses={200: ServiceProviderOwnerSerializer})
    def get(self, request):
        provider = get_current_provider(request.user)
        self.check_object_permissions(request, provider)
        return Response(ServiceProviderOwnerSerializer(provider, context={"request": request}).data)

    @extend_schema(
        request=ServiceProviderOwnerSerializer,
        responses={200: ServiceProviderOwnerSerializer},
    )
    def patch(self, request):
        provider = get_current_provider(request.user)
        self.check_object_permissions(request, provider)
        serializer = ServiceProviderOwnerSerializer(
            provider,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        emit_service_event(
            actor=request.user,
            action="service_provider.updated",
            entity=provider,
            metadata={"fields": sorted(serializer.validated_data)},
        )
        return Response(ServiceProviderOwnerSerializer(provider, context={"request": request}).data)


class ProviderProfileSubmitView(APIView):
    serializer_class = ServiceProviderOwnerSerializer
    permission_classes = [IsAuthenticated, IsServiceProviderOwner]

    @extend_schema(
        responses={
            200: ServiceProviderOwnerSerializer,
            400: OpenApiResponse(description="Profile is incomplete or cannot be submitted."),
        }
    )
    def post(self, request):
        provider = get_current_provider(request.user)
        self.check_object_permissions(request, provider)
        if provider.status not in [
            ProviderStatus.DRAFT,
            ProviderStatus.REJECTED,
            ProviderStatus.NEEDS_MORE_INFORMATION,
        ]:
            return Response(
                {"detail": "This profile cannot be submitted from its current status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        completion = validate_provider_submission(provider)
        if not completion["is_complete"]:
            return Response({"completion": completion}, status=status.HTTP_400_BAD_REQUEST)
        provider.submit_for_review()
        emit_service_event(
            actor=request.user,
            action="service_provider.submitted",
            entity=provider,
            metadata={"status": provider.status},
        )
        return Response(ServiceProviderOwnerSerializer(provider, context={"request": request}).data)


class ProviderProfileDeactivateView(APIView):
    serializer_class = ServiceProviderOwnerSerializer
    permission_classes = [IsAuthenticated, IsServiceProviderOwner]

    @extend_schema(responses={200: ServiceProviderOwnerSerializer})
    def post(self, request):
        provider = get_current_provider(request.user)
        self.check_object_permissions(request, provider)
        if provider.status != ProviderStatus.ACTIVE:
            return Response(
                {"detail": "Only active provider profiles can be deactivated."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        provider.deactivate()
        emit_service_event(
            actor=request.user,
            action="service_provider.deactivated",
            entity=provider,
        )
        return Response(ServiceProviderOwnerSerializer(provider, context={"request": request}).data)


class ProviderOwnedMixin:
    permission_classes = [IsAuthenticated, IsServiceProviderOwner]

    def get_provider(self) -> ServiceProvider:
        return get_current_provider(self.request.user)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.model.objects.none()
        return self.model.objects.filter(provider=self.get_provider())


class ProviderTradeManagementViewSet(
    ProviderOwnedMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    model = ProviderTrade
    queryset = ProviderTrade.objects.none()
    serializer_class = ProviderTradeWriteSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self, "swagger_fake_view", False):
            return context
        context["provider"] = self.get_provider()
        return context

    def perform_create(self, serializer):
        provider = self.get_provider()
        if not provider.trades.exists():
            serializer.validated_data["is_primary"] = True
        trade = serializer.save()
        emit_service_event(
            actor=self.request.user,
            action="service_provider.trade_added",
            entity=provider,
            metadata={"trade_id": str(trade.id), "category": trade.category.slug},
        )

    def perform_update(self, serializer):
        trade = serializer.save()
        emit_service_event(
            actor=self.request.user,
            action="service_provider.trade_updated",
            entity=trade.provider,
            metadata={"trade_id": str(trade.id)},
        )

    def perform_destroy(self, instance):
        provider = instance.provider
        trade_id = str(instance.id)
        instance.delete()
        if not provider.trades.filter(is_primary=True, status=ProviderTradeStatus.ACTIVE).exists():
            replacement = provider.trades.filter(status=ProviderTradeStatus.ACTIVE).first()
            if replacement:
                replacement.is_primary = True
                replacement.save(update_fields=["is_primary", "updated_at"])
        emit_service_event(
            actor=self.request.user,
            action="service_provider.trade_removed",
            entity=provider,
            metadata={"trade_id": trade_id},
        )


class ServiceAreaManagementViewSet(
    ProviderOwnedMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    model = ServiceArea
    queryset = ServiceArea.objects.none()
    serializer_class = ServiceAreaWriteSerializer

    def perform_create(self, serializer):
        provider = self.get_provider()
        if not provider.service_areas.exists():
            serializer.validated_data["is_primary"] = True
        area = serializer.save(provider=provider)
        emit_service_event(
            actor=self.request.user,
            action="service_provider.service_area_added",
            entity=provider,
            metadata={"service_area_id": str(area.id)},
        )

    def perform_update(self, serializer):
        area = serializer.save()
        emit_service_event(
            actor=self.request.user,
            action="service_provider.service_area_updated",
            entity=area.provider,
            metadata={"service_area_id": str(area.id)},
        )

    def perform_destroy(self, instance):
        provider = instance.provider
        area_id = str(instance.id)
        instance.delete()
        if not provider.service_areas.filter(is_primary=True).exists():
            replacement = provider.service_areas.first()
            if replacement:
                replacement.is_primary = True
                replacement.save(update_fields=["is_primary", "updated_at"])
        emit_service_event(
            actor=self.request.user,
            action="service_provider.service_area_removed",
            entity=provider,
            metadata={"service_area_id": area_id},
        )


class PortfolioImageManagementViewSet(
    ProviderOwnedMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    model = PortfolioImage
    queryset = PortfolioImage.objects.none()
    parser_classes = [MultiPartParser, FormParser]
    throttle_scope_by_action = {"create": "service_portfolio_upload"}

    def get_serializer_class(self):
        if self.action == "create":
            return PortfolioImageSerializer
        return PortfolioImageMetadataSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if getattr(self, "swagger_fake_view", False):
            return context
        context["provider"] = self.get_provider()
        return context

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PortfolioImage.objects.none()
        return (
            PortfolioImage.objects.filter(provider=self.get_provider())
            .select_related("category")
            .order_by("display_order", "created_at")
        )

    def perform_create(self, serializer):
        provider = self.get_provider()
        image = serializer.save()
        emit_service_event(
            actor=self.request.user,
            action="service_provider.portfolio_uploaded",
            entity=provider,
            metadata={"portfolio_image_id": str(image.id), "is_cover": image.is_cover},
        )

    def perform_update(self, serializer):
        image = serializer.save()
        emit_service_event(
            actor=self.request.user,
            action="service_provider.portfolio_updated",
            entity=image.provider,
            metadata={"portfolio_image_id": str(image.id)},
        )

    def perform_destroy(self, instance):
        provider = instance.provider
        image_id = str(instance.id)
        image_file = instance.image
        was_cover = instance.is_cover
        instance.delete()
        image_file.delete(save=False)
        if was_cover and not provider.portfolio_images.filter(is_cover=True).exists():
            replacement = provider.portfolio_images.order_by("display_order", "created_at").first()
            if replacement:
                replacement.set_as_cover()
        emit_service_event(
            actor=self.request.user,
            action="service_provider.portfolio_deleted",
            entity=provider,
            metadata={"portfolio_image_id": image_id},
        )

    @extend_schema(
        parameters=[OpenApiParameter("pk", OpenApiTypes.UUID, OpenApiParameter.PATH)],
        responses={200: PortfolioImagePublicSerializer},
    )
    @action(detail=True, methods=["post"], url_path="cover")
    def cover(self, request, pk=None):
        image = self.get_object()
        image.set_as_cover()
        emit_service_event(
            actor=request.user,
            action="service_provider.portfolio_cover_changed",
            entity=image.provider,
            metadata={"portfolio_image_id": str(image.id)},
        )
        return Response(PortfolioImageMetadataSerializer(image, context={"request": request}).data)

    @extend_schema(
        request=PortfolioReorderSerializer,
        responses={200: PortfolioImageMetadataSerializer(many=True)},
    )
    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request):
        serializer = PortfolioReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = self.get_provider()
        image_map = {str(image.id): image for image in provider.portfolio_images.all()}
        for item in serializer.validated_data["items"]:
            image = image_map.get(str(item["id"]))
            if image:
                image.display_order = int(item["display_order"])
                image.save(update_fields=["display_order", "updated_at"])
        emit_service_event(
            actor=request.user,
            action="service_provider.portfolio_reordered",
            entity=provider,
        )
        return Response(
            PortfolioImageMetadataSerializer(
                self.get_queryset(),
                many=True,
                context={"request": request},
            ).data
        )


class AdminServiceProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdminServiceProviderSerializer
    permission_classes = [IsAuthenticated, IsServicesAdmin]
    filterset_fields = ["status", "provider_type", "state", "city"]
    search_fields = ["business_name", "headline", "biography", "user__email"]
    ordering_fields = ["created_at", "submitted_at", "business_name", "status"]
    ordering = ["-submitted_at", "-created_at"]

    def get_queryset(self):
        return provider_queryset().annotate(portfolio_count=Count("portfolio_images"))

    def _decision_serializer(self):
        serializer = AdminDecisionSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        return serializer

    def _ensure_not_self_review(self, provider):
        if provider.user_id == self.request.user.id:
            return Response(
                {"detail": "Admins cannot review their own provider profile."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        provider = self.get_object()
        if response := self._ensure_not_self_review(provider):
            return response
        provider.approve(reviewer=request.user)
        emit_service_event(
            actor=request.user,
            action="service_provider.approved",
            entity=provider,
        )
        return Response(self.get_serializer(provider).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        provider = self.get_object()
        if response := self._ensure_not_self_review(provider):
            return response
        serializer = self._decision_serializer()
        reason = serializer.validated_data.get("reason", "").strip()
        if not reason:
            return Response({"reason": ["Rejection reason is required."]}, status=400)
        provider.reject(reviewer=request.user, reason=reason)
        provider.review_notes = serializer.validated_data.get("review_notes", "")
        provider.save(update_fields=["review_notes", "updated_at"])
        emit_service_event(
            actor=request.user,
            action="service_provider.rejected",
            entity=provider,
            metadata={"reason": reason},
        )
        return Response(self.get_serializer(provider).data)

    @action(detail=True, methods=["post"], url_path="request-info")
    def request_info(self, request, pk=None):
        provider = self.get_object()
        if response := self._ensure_not_self_review(provider):
            return response
        serializer = self._decision_serializer()
        message = serializer.validated_data.get("message", "").strip()
        if not message:
            return Response({"message": ["More-information message is required."]}, status=400)
        provider.request_more_information(reviewer=request.user, message=message)
        provider.review_notes = serializer.validated_data.get("review_notes", "")
        provider.save(update_fields=["review_notes", "updated_at"])
        emit_service_event(
            actor=request.user,
            action="service_provider.more_info_requested",
            entity=provider,
        )
        return Response(self.get_serializer(provider).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        provider = self.get_object()
        serializer = self._decision_serializer()
        reason = serializer.validated_data.get("reason", "").strip()
        if not reason:
            return Response({"reason": ["Suspension reason is required."]}, status=400)
        provider.suspend(reviewer=request.user, reason=reason)
        provider.review_notes = serializer.validated_data.get("review_notes", "")
        provider.save(update_fields=["review_notes", "updated_at"])
        emit_service_event(
            actor=request.user,
            action="service_provider.suspended",
            entity=provider,
            metadata={"reason": reason},
        )
        return Response(self.get_serializer(provider).data)

    @action(detail=True, methods=["post"])
    def reactivate(self, request, pk=None):
        provider = self.get_object()
        if response := self._ensure_not_self_review(provider):
            return response
        provider.reactivate(reviewer=request.user)
        emit_service_event(
            actor=request.user,
            action="service_provider.reactivated",
            entity=provider,
        )
        return Response(self.get_serializer(provider).data)
