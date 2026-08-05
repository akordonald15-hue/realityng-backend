from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, OpenApiTypes, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from apps.accounts.services import user_is_admin
from apps.services.choices import (
    ProviderStatus,
    ProviderTradeStatus,
    ServiceReviewFlagReason,
    ServiceReviewStatus,
)
from apps.services.filters import PublicServiceProviderFilter
from apps.services.models import (
    PortfolioImage,
    ProviderTrade,
    QuoteRequest,
    ServiceArea,
    ServiceProvider,
    ServiceReview,
    ServiceReviewFlag,
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
    AdminReviewDecisionSerializer,
    AdminServiceProviderSerializer,
    AdminServiceReviewSerializer,
    PortfolioImageMetadataSerializer,
    PortfolioImagePublicSerializer,
    PortfolioImageSerializer,
    PortfolioReorderSerializer,
    ProviderReviewResponseSerializer,
    ProviderTradeWriteSerializer,
    PublicServiceProviderDetailSerializer,
    PublicServiceProviderListSerializer,
    QuoteRequestCreateSerializer,
    QuoteRequestSerializer,
    ServiceAreaWriteSerializer,
    ServiceProviderOwnerSerializer,
    ServiceReviewCreateSerializer,
    ServiceReviewFlagSerializer,
    ServiceReviewPublicSerializer,
    ServiceReviewSerializer,
    ServiceReviewUpdateSerializer,
    TradeCategorySerializer,
    active_public_provider_queryset,
    validate_provider_submission,
)
from apps.services.services import emit_service_event, recalculate_provider_rating


class ActionScopedThrottleMixin:
    throttle_scope_by_action: dict[str, str] = {}
    throttle_classes = [AnonRateThrottle, UserRateThrottle, ScopedRateThrottle]

    def get_throttles(self):
        if getattr(self, "action", None) in self.throttle_scope_by_action:
            self.throttle_scope = self.throttle_scope_by_action[self.action]
        return super().get_throttles()


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


def quote_request_queryset():
    return QuoteRequest.objects.select_related(
        "customer",
        "provider",
        "service_category",
    )


def filter_quote_requests(queryset, request):
    status_value = request.query_params.get("status")
    search = request.query_params.get("search")
    ordering = request.query_params.get("ordering", "-created_at")
    if status_value:
        queryset = queryset.filter(status=status_value)
    if search:
        queryset = queryset.filter(
            Q(project_title__icontains=search)
            | Q(project_description__icontains=search)
            | Q(customer_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
        )
    if ordering == "oldest":
        return queryset.order_by("created_at")
    return queryset.order_by("-created_at")


def review_queryset():
    return ServiceReview.objects.select_related(
        "booking__service_category",
        "customer",
        "provider",
    ).prefetch_related("flags")


def filter_reviews(queryset, request):
    status_value = request.query_params.get("status")
    provider = request.query_params.get("provider")
    customer = request.query_params.get("customer")
    rating = request.query_params.get("rating")
    flagged = request.query_params.get("flagged")
    ordering = request.query_params.get("ordering", "newest")
    if status_value:
        queryset = queryset.filter(status=status_value)
    if provider:
        queryset = queryset.filter(provider_id=provider)
    if customer:
        queryset = queryset.filter(customer_id=customer)
    if rating:
        queryset = queryset.filter(rating=rating)
    if flagged in ["true", "1"]:
        queryset = queryset.filter(flags__deleted_at__isnull=True).distinct()
    if request.query_params.get("recommended") in ["true", "1"]:
        queryset = queryset.filter(would_recommend=True)
    if ordering == "highest":
        return queryset.order_by("-rating", "-created_at")
    if ordering == "lowest":
        return queryset.order_by("rating", "-created_at")
    if ordering == "oldest":
        return queryset.order_by("created_at")
    return queryset.order_by("-created_at")


def client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


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


class PublicQuoteRequestCreateViewSet(
    ActionScopedThrottleMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = QuoteRequestCreateSerializer
    permission_classes = [AllowAny]
    throttle_scope_by_action = {"create": "service_quote_request_create"}

    @extend_schema(
        request=QuoteRequestCreateSerializer,
        responses={201: QuoteRequestSerializer},
    )
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data["provider_slug"] = kwargs["provider_slug"]
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        quote_request = serializer.save()
        emit_service_event(
            actor=request.user if request.user.is_authenticated else None,
            action="service_quote.submitted",
            entity=quote_request,
            metadata={
                "provider_id": str(quote_request.provider_id),
                "status": quote_request.status,
            },
        )
        return Response(
            QuoteRequestSerializer(quote_request, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ProviderQuoteRequestViewSet(
    ActionScopedThrottleMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = QuoteRequestSerializer
    permission_classes = [IsAuthenticated, IsServiceProviderOwner]
    throttle_scope_by_action = {"list": "service_quote_request_manage"}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return QuoteRequest.objects.none()
        provider = self.get_provider()
        queryset = quote_request_queryset().filter(provider=provider)
        return filter_quote_requests(queryset, self.request)

    def get_provider(self):
        return get_current_provider(self.request.user)

    def _transition(self, request, quote_request, action_name):
        self.check_object_permissions(request, quote_request)
        if action_name == "viewed":
            quote_request.mark_viewed()
            event = "service_quote.viewed"
        elif action_name == "responded":
            quote_request.mark_responded()
            event = "service_quote.responded"
        else:
            quote_request.close()
            event = "service_quote.closed"
        emit_service_event(
            actor=request.user,
            action=event,
            entity=quote_request,
            metadata={"status": quote_request.status},
        )
        return Response(self.get_serializer(quote_request).data)

    @extend_schema(responses={200: QuoteRequestSerializer})
    @action(detail=True, methods=["post"], url_path="mark-viewed")
    def mark_viewed(self, request, pk=None):
        return self._transition(request, self.get_object(), "viewed")

    @extend_schema(responses={200: QuoteRequestSerializer})
    @action(detail=True, methods=["post"], url_path="mark-responded")
    def mark_responded(self, request, pk=None):
        return self._transition(request, self.get_object(), "responded")

    @extend_schema(responses={200: QuoteRequestSerializer})
    @action(detail=True, methods=["post"], url_path="close")
    def close_request(self, request, pk=None):
        return self._transition(request, self.get_object(), "closed")


class AdminQuoteRequestViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = QuoteRequestSerializer
    permission_classes = [IsAuthenticated, IsServicesAdmin]

    def get_queryset(self):
        queryset = quote_request_queryset()
        provider = self.request.query_params.get("provider")
        if provider:
            queryset = queryset.filter(provider_id=provider)
        return filter_quote_requests(queryset, self.request)

    @extend_schema(responses={200: QuoteRequestSerializer})
    @action(detail=True, methods=["post"], url_path="close")
    def close_request(self, request, pk=None):
        quote_request = self.get_object()
        quote_request.close()
        emit_service_event(
            actor=request.user,
            action="service_quote.admin_closed",
            entity=quote_request,
            metadata={"status": quote_request.status},
        )
        return Response(self.get_serializer(quote_request).data)


class ServiceReviewViewSet(
    ActionScopedThrottleMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    throttle_scope_by_action = {
        "create": "service_review_create",
        "partial_update": "service_review_update",
        "respond": "service_review_response",
        "flag": "service_review_flag",
    }

    def get_serializer_class(self):
        if self.action == "create":
            return ServiceReviewCreateSerializer
        if self.action in ["update", "partial_update"]:
            return ServiceReviewUpdateSerializer
        if self.action == "respond":
            return ProviderReviewResponseSerializer
        if self.action == "flag":
            return ServiceReviewFlagSerializer
        return ServiceReviewSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ServiceReview.objects.none()
        user = self.request.user
        if user_is_admin(user):
            return review_queryset()
        return review_queryset().filter(Q(customer=user) | Q(provider__user=user))

    def perform_create(self, serializer):
        review = serializer.save(
            creation_ip=client_ip(self.request),
            user_agent=self.request.META.get("HTTP_USER_AGENT", "")[:2000],
        )
        emit_service_event(
            actor=self.request.user,
            action="service_review.created",
            entity=review,
            metadata={"provider_id": str(review.provider_id), "status": review.status},
        )
        return review

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = self.perform_create(serializer)
        return Response(
            ServiceReviewSerializer(review, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        review = self.get_object()
        if review.customer_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        edit_deadline = review.created_at + timedelta(
            hours=getattr(settings, "SERVICE_REVIEW_EDIT_WINDOW_HOURS", 48)
        )
        if review.status != ServiceReviewStatus.PENDING or timezone.now() > edit_deadline:
            return Response(
                {"detail": "This review can no longer be edited."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        emit_service_event(
            actor=request.user,
            action="service_review.updated",
            entity=review,
            metadata={"status": review.status},
        )
        return Response(ServiceReviewSerializer(review, context={"request": request}).data)

    @extend_schema(responses={200: ServiceReviewSerializer(many=True)})
    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        queryset = filter_reviews(review_queryset().filter(customer=request.user), request)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ServiceReviewSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        serializer = ServiceReviewSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        request=ProviderReviewResponseSerializer,
        responses={200: ServiceReviewSerializer},
    )
    @action(detail=True, methods=["post"], url_path="respond")
    def respond(self, request, pk=None):
        review = self.get_object()
        if review.provider.user_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if review.status != ServiceReviewStatus.PUBLISHED:
            return Response(
                {"detail": "Only published reviews can receive provider responses."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if review.provider_response:
            return Response(
                {"detail": "This review already has a provider response."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review.respond(serializer.validated_data["response"])
        emit_service_event(
            actor=request.user,
            action="service_review.provider_responded",
            entity=review,
        )
        return Response(ServiceReviewSerializer(review, context={"request": request}).data)

    @extend_schema(request=ServiceReviewFlagSerializer, responses={200: ServiceReviewSerializer})
    @action(detail=True, methods=["post"], url_path="flag")
    def flag(self, request, pk=None):
        review = self.get_object()
        if review.status not in [
            ServiceReviewStatus.PUBLISHED,
            ServiceReviewStatus.DISPUTED,
            ServiceReviewStatus.FLAGGED,
        ]:
            return Response(
                {"detail": "This review is not available for flagging."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        flag, created = ServiceReviewFlag.objects.get_or_create(
            review=review,
            user=request.user,
            defaults=serializer.validated_data,
        )
        if not created:
            return Response(
                {"detail": "You have already flagged this review."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        active_flag_count = review.flags.count()
        if (
            active_flag_count >= 3
            or flag.reason
            in [
                ServiceReviewFlagReason.PRIVACY_CONCERN,
                ServiceReviewFlagReason.CONFLICT_OF_INTEREST,
            ]
        ):
            review.status = ServiceReviewStatus.FLAGGED
            review.save(update_fields=["status", "updated_at"])
            recalculate_provider_rating(review.provider)
        emit_service_event(
            actor=request.user,
            action="service_review.flagged",
            entity=review,
            metadata={"reason": flag.reason, "flag_count": active_flag_count},
        )
        return Response(ServiceReviewSerializer(review, context={"request": request}).data)


class PublicProviderReviewViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServiceReviewPublicSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ServiceReview.objects.none()
        provider = get_object_or_404(
            active_public_provider_queryset(),
            slug=self.kwargs["provider_slug"],
        )
        queryset = review_queryset().filter(
            provider=provider,
            status=ServiceReviewStatus.PUBLISHED,
        )
        return filter_reviews(queryset, self.request)


class ProviderReviewViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServiceReviewSerializer
    permission_classes = [IsAuthenticated, IsServiceProviderOwner]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ServiceReview.objects.none()
        provider = get_current_provider(self.request.user)
        return filter_reviews(review_queryset().filter(provider=provider), self.request)


class AdminServiceReviewViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdminServiceReviewSerializer
    permission_classes = [IsAuthenticated, IsServicesAdmin]

    def get_queryset(self):
        return filter_reviews(review_queryset(), self.request)

    def _decision_reason(self, request, required: bool) -> str | Response:
        serializer = AdminReviewDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "").strip()
        if required and not reason:
            return Response({"reason": ["A moderation reason is required."]}, status=400)
        return reason

    def _return_review(self, request, review, action_name):
        recalculate_provider_rating(review.provider)
        emit_service_event(
            actor=request.user,
            action=action_name,
            entity=review,
            metadata={"status": review.status},
        )
        return Response(self.get_serializer(review).data)

    @extend_schema(
        request=AdminReviewDecisionSerializer,
        responses={200: AdminServiceReviewSerializer},
    )
    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        review = self.get_object()
        review.publish()
        return self._return_review(request, review, "service_review.published")

    @extend_schema(
        request=AdminReviewDecisionSerializer,
        responses={200: AdminServiceReviewSerializer},
    )
    @action(detail=True, methods=["post"], url_path="hide")
    def hide(self, request, pk=None):
        review = self.get_object()
        reason = self._decision_reason(request, required=True)
        if isinstance(reason, Response):
            return reason
        review.hide(reason)
        return self._return_review(request, review, "service_review.hidden")

    @extend_schema(
        request=AdminReviewDecisionSerializer,
        responses={200: AdminServiceReviewSerializer},
    )
    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        review = self.get_object()
        review.restore()
        return self._return_review(request, review, "service_review.restored")

    @extend_schema(
        request=AdminReviewDecisionSerializer,
        responses={200: AdminServiceReviewSerializer},
    )
    @action(detail=True, methods=["post"], url_path="remove")
    def remove(self, request, pk=None):
        review = self.get_object()
        reason = self._decision_reason(request, required=True)
        if isinstance(reason, Response):
            return reason
        review.remove(reason)
        return self._return_review(request, review, "service_review.removed")

    @extend_schema(
        request=AdminReviewDecisionSerializer,
        responses={200: AdminServiceReviewSerializer},
    )
    @action(detail=True, methods=["post"], url_path="mark-disputed")
    def mark_disputed(self, request, pk=None):
        review = self.get_object()
        reason = self._decision_reason(request, required=True)
        if isinstance(reason, Response):
            return reason
        review.mark_disputed(reason)
        return self._return_review(request, review, "service_review.disputed")

    @extend_schema(responses={200: QuoteRequestSerializer})
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_request(self, request, pk=None):
        quote_request = self.get_object()
        quote_request.cancel()
        emit_service_event(
            actor=request.user,
            action="service_quote.admin_cancelled",
            entity=quote_request,
            metadata={"status": quote_request.status},
        )
        return Response(self.get_serializer(quote_request).data)
