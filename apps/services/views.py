from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db.models import Avg, Count, Prefetch, Q
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
    ProviderAppealStatus,
    ProviderStatus,
    ProviderSuspensionType,
    ProviderTradeStatus,
    QuoteRequestStatus,
    ServiceBookingStatus,
    ServiceComplaintStatus,
    ServiceReviewFlagReason,
    ServiceReviewStatus,
)
from apps.services.filters import PublicServiceProviderFilter
from apps.services.models import (
    PortfolioImage,
    ProviderAppeal,
    ProviderTrade,
    QuoteRequest,
    ServiceArea,
    ServiceBooking,
    ServiceComplaint,
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
    AdminAppealDecisionSerializer,
    AdminComplaintDecisionSerializer,
    AdminDecisionSerializer,
    AdminReviewDecisionSerializer,
    AdminServiceComplaintSerializer,
    AdminServiceProviderSerializer,
    AdminServiceReviewSerializer,
    AdminServicesDashboardSerializer,
    CustomerServicesDashboardSerializer,
    PortfolioImageMetadataSerializer,
    PortfolioImagePublicSerializer,
    PortfolioImageSerializer,
    PortfolioReorderSerializer,
    ProviderAppealSerializer,
    ProviderReviewResponseSerializer,
    ProviderServicesDashboardSerializer,
    ProviderTradeWriteSerializer,
    PublicServiceProviderDetailSerializer,
    PublicServiceProviderListSerializer,
    QuoteRequestCreateSerializer,
    QuoteRequestSerializer,
    ServiceAreaWriteSerializer,
    ServiceComplaintCreateSerializer,
    ServiceComplaintEvidenceSerializer,
    ServiceComplaintSerializer,
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
        if provider.status == ProviderStatus.SUSPENDED:
            return Response(
                {"detail": "Suspended provider profiles cannot be edited."},
                status=status.HTTP_403_FORBIDDEN,
            )
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
    blocked_mutation_statuses = {ProviderStatus.SUSPENDED, ProviderStatus.ARCHIVED}

    def get_provider(self) -> ServiceProvider:
        return get_current_provider(self.request.user)

    def ensure_provider_can_mutate(self, provider: ServiceProvider):
        if provider.status in self.blocked_mutation_statuses:
            return Response(
                {"detail": "This provider profile is restricted from making changes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def create(self, request, *args, **kwargs):
        if response := self.ensure_provider_can_mutate(self.get_provider()):
            return response
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if response := self.ensure_provider_can_mutate(self.get_provider()):
            return response
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if response := self.ensure_provider_can_mutate(self.get_provider()):
            return response
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if response := self.ensure_provider_can_mutate(self.get_provider()):
            return response
        return super().destroy(request, *args, **kwargs)

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


def complaint_queryset():
    return ServiceComplaint.objects.select_related(
        "complainant",
        "provider",
        "quote_request",
        "review",
        "booking",
        "assigned_admin",
    ).prefetch_related("evidence__uploaded_by")


def appeal_queryset():
    return ProviderAppeal.objects.select_related(
        "provider",
        "submitted_by",
        "decided_by",
    )


def filter_complaints(queryset, request):
    status_value = request.query_params.get("status")
    category = request.query_params.get("category")
    provider = request.query_params.get("provider")
    search = request.query_params.get("search")
    ordering = request.query_params.get("ordering", "newest")
    if status_value:
        queryset = queryset.filter(status=status_value)
    if category:
        queryset = queryset.filter(category=category)
    if provider:
        queryset = queryset.filter(provider_id=provider)
    if search:
        queryset = queryset.filter(
            Q(subject__icontains=search)
            | Q(description__icontains=search)
            | Q(provider__business_name__icontains=search)
            | Q(complainant__email__icontains=search)
        )
    if ordering == "oldest":
        return queryset.order_by("created_at")
    return queryset.order_by("-created_at")


def filter_appeals(queryset, request):
    status_value = request.query_params.get("status")
    appeal_type = request.query_params.get("appeal_type")
    provider = request.query_params.get("provider")
    if status_value:
        queryset = queryset.filter(status=status_value)
    if appeal_type:
        queryset = queryset.filter(appeal_type=appeal_type)
    if provider:
        queryset = queryset.filter(provider_id=provider)
    return queryset.order_by("-created_at")


def count_by_status(queryset, choices) -> dict[str, int]:
    counts = dict.fromkeys([choice.value for choice in choices], 0)
    for item in queryset.values("status").annotate(total=Count("id")):
        counts[item["status"]] = item["total"]
    return counts


def unique_in_order(items) -> list:
    seen = set()
    ordered = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def activity_item(*, item_id, title, description="", status_label="", timestamp, href="") -> dict:
    return {
        "id": str(item_id),
        "title": title,
        "description": description,
        "status": status_label,
        "timestamp": timestamp,
        "href": href,
    }


def newest_activity(*groups, limit=8) -> list[dict]:
    activity = [item for group in groups for item in group]
    return sorted(activity, key=lambda item: item["timestamp"], reverse=True)[:limit]


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


class ServiceComplaintViewSet(
    ActionScopedThrottleMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    throttle_scope_by_action = {"create": "service_complaint_create"}

    def get_serializer_class(self):
        if self.action == "create":
            return ServiceComplaintCreateSerializer
        return ServiceComplaintSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ServiceComplaint.objects.none()
        queryset = complaint_queryset().filter(complainant=self.request.user)
        return filter_complaints(queryset, self.request)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complaint = serializer.save()
        emit_service_event(
            actor=request.user,
            action="service_complaint.created",
            entity=complaint,
            metadata={
                "provider_id": str(complaint.provider_id),
                "category": complaint.category,
                "status": complaint.status,
            },
        )
        return Response(
            ServiceComplaintSerializer(complaint, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        request=ServiceComplaintEvidenceSerializer,
        responses={201: ServiceComplaintEvidenceSerializer},
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="evidence",
        parser_classes=[MultiPartParser, FormParser],
    )
    def add_evidence(self, request, pk=None):
        complaint = self.get_object()
        serializer = ServiceComplaintEvidenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        evidence = serializer.save(complaint=complaint, uploaded_by=request.user)
        emit_service_event(
            actor=request.user,
            action="service_complaint.evidence_uploaded",
            entity=complaint,
            metadata={"evidence_id": str(evidence.id)},
        )
        return Response(
            ServiceComplaintEvidenceSerializer(evidence, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ProviderComplaintViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ServiceComplaintSerializer
    permission_classes = [IsAuthenticated, IsServiceProviderOwner]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ServiceComplaint.objects.none()
        provider = get_current_provider(self.request.user)
        queryset = complaint_queryset().filter(
            Q(provider=provider) | Q(complainant=self.request.user)
        )
        return filter_complaints(queryset.distinct(), self.request)


class ProviderAppealViewSet(
    ActionScopedThrottleMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ProviderAppealSerializer
    permission_classes = [IsAuthenticated, IsServiceProviderOwner]
    throttle_scope_by_action = {"create": "service_provider_appeal_create"}

    def get_provider(self):
        return get_current_provider(self.request.user)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return ProviderAppeal.objects.none()
        return filter_appeals(appeal_queryset().filter(provider=self.get_provider()), self.request)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if not getattr(self, "swagger_fake_view", False):
            context["provider"] = self.get_provider()
        return context

    def perform_create(self, serializer):
        provider = self.get_provider()
        appeal = serializer.save(provider=provider, submitted_by=self.request.user)
        provider.appeal_status = appeal.status
        provider.save(update_fields=["appeal_status", "updated_at"])
        emit_service_event(
            actor=self.request.user,
            action="service_provider.appeal_submitted",
            entity=appeal,
            metadata={"provider_id": str(provider.id), "appeal_type": appeal.appeal_type},
        )


class AdminServiceComplaintViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AdminServiceComplaintSerializer
    permission_classes = [IsAuthenticated, IsServicesAdmin]
    filterset_fields = ["status", "category", "complaint_type", "provider"]
    search_fields = ["subject", "description", "provider__business_name", "complainant__email"]
    ordering_fields = ["created_at", "updated_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return filter_complaints(complaint_queryset(), self.request)

    def _decision_serializer(self):
        serializer = AdminComplaintDecisionSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        return serializer

    def _transition(self, request, complaint, status_value, event_name, requires_notes=False):
        serializer = self._decision_serializer()
        notes = serializer.validated_data.get("notes", "").strip()
        admin_notes = serializer.validated_data.get("admin_notes", "").strip()
        if requires_notes and not notes:
            return Response({"notes": ["Notes are required for this action."]}, status=400)
        complaint.set_status(new_status=status_value, actor=request.user, notes=notes)
        if admin_notes:
            complaint.admin_notes = admin_notes
            complaint.save(update_fields=["admin_notes", "updated_at"])
        emit_service_event(
            actor=request.user,
            action=event_name,
            entity=complaint,
            metadata={"status": complaint.status},
        )
        return Response(self.get_serializer(complaint).data)

    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        return self._transition(
            request,
            self.get_object(),
            ServiceComplaintStatus.UNDER_REVIEW,
            "service_complaint.under_review",
        )

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        return self._transition(
            request,
            self.get_object(),
            ServiceComplaintStatus.RESOLVED,
            "service_complaint.resolved",
            requires_notes=True,
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._transition(
            request,
            self.get_object(),
            ServiceComplaintStatus.REJECTED,
            "service_complaint.rejected",
            requires_notes=True,
        )

    @action(detail=True, methods=["post"])
    def escalate(self, request, pk=None):
        return self._transition(
            request,
            self.get_object(),
            ServiceComplaintStatus.ESCALATED,
            "service_complaint.escalated",
            requires_notes=True,
        )

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        return self._transition(
            request,
            self.get_object(),
            ServiceComplaintStatus.CLOSED,
            "service_complaint.closed",
        )

    @action(detail=True, methods=["post"], url_path="await-customer")
    def await_customer(self, request, pk=None):
        return self._transition(
            request,
            self.get_object(),
            ServiceComplaintStatus.AWAITING_CUSTOMER,
            "service_complaint.awaiting_customer",
        )

    @action(detail=True, methods=["post"], url_path="await-provider")
    def await_provider(self, request, pk=None):
        return self._transition(
            request,
            self.get_object(),
            ServiceComplaintStatus.AWAITING_PROVIDER,
            "service_complaint.awaiting_provider",
        )


class AdminProviderAppealViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProviderAppealSerializer
    permission_classes = [IsAuthenticated, IsServicesAdmin]
    filterset_fields = ["status", "appeal_type", "provider"]
    search_fields = ["reason", "provider__business_name", "submitted_by__email"]
    ordering_fields = ["created_at", "updated_at", "status"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return filter_appeals(appeal_queryset(), self.request)

    def _decision_serializer(self):
        serializer = AdminAppealDecisionSerializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        return serializer

    def _decide(self, request, appeal, status_value, event_name):
        serializer = self._decision_serializer()
        appeal.decide(
            status_value=status_value,
            actor=request.user,
            notes=serializer.validated_data.get("notes", "").strip(),
        )
        if status_value == ProviderAppealStatus.APPROVED:
            if appeal.appeal_type == "suspension":
                appeal.provider.reactivate(reviewer=request.user)
            else:
                appeal.provider.last_warning_reason = ""
                appeal.provider.save(update_fields=["last_warning_reason", "updated_at"])
        emit_service_event(
            actor=request.user,
            action=event_name,
            entity=appeal,
            metadata={"status": appeal.status, "provider_id": str(appeal.provider_id)},
        )
        return Response(self.get_serializer(appeal).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._decide(
            request,
            self.get_object(),
            ProviderAppealStatus.APPROVED,
            "service_provider.appeal_approved",
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._decide(
            request,
            self.get_object(),
            ProviderAppealStatus.REJECTED,
            "service_provider.appeal_rejected",
        )

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        return self._decide(
            request,
            self.get_object(),
            ProviderAppealStatus.REOPENED,
            "service_provider.appeal_reopened",
        )


class CustomerServicesDashboardView(APIView):
    serializer_class = CustomerServicesDashboardSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: CustomerServicesDashboardSerializer})
    def get(self, request):
        user = request.user
        quote_requests = quote_request_queryset().filter(customer=user).order_by("-created_at")
        submitted_reviews = review_queryset().filter(customer=user).order_by("-created_at")
        eligible_reviews = (
            ServiceBooking.objects.filter(
                customer=user,
                status=ServiceBookingStatus.COMPLETED,
                completed_at__isnull=False,
                review__isnull=True,
            )
            .select_related("provider", "service_category")
            .order_by("-completed_at")
        )
        provider_ids = unique_in_order(quote_requests.values_list("provider_id", flat=True)[:12])
        recent_providers = active_public_provider_queryset().filter(id__in=provider_ids)
        recommended_providers = active_public_provider_queryset().order_by(
            "-average_rating",
            "-published_review_count",
            "business_name",
        )[:4]
        categories = (
            TradeCategory.objects.filter(is_active=True, parent__isnull=True)
            .prefetch_related(
                Prefetch(
                    "children",
                    queryset=TradeCategory.objects.filter(is_active=True).order_by(
                        "display_order", "name"
                    ),
                    to_attr="prefetched_children",
                )
            )
            .order_by("display_order", "name")[:8]
        )

        activity = newest_activity(
            [
                activity_item(
                    item_id=f"quote-{item.id}",
                    title=f"Quote requested: {item.project_title}",
                    description=item.provider.business_name,
                    status_label=item.status,
                    timestamp=item.created_at,
                    href="/dashboard/services",
                )
                for item in quote_requests[:5]
            ],
            [
                activity_item(
                    item_id=f"review-{item.id}",
                    title=f"Review submitted: {item.title}",
                    description=item.provider.business_name,
                    status_label=item.status,
                    timestamp=item.created_at,
                    href="/dashboard/services/reviews",
                )
                for item in submitted_reviews[:5]
            ],
            [
                activity_item(
                    item_id=f"eligible-review-{item.id}",
                    title=f"Review available: {item.title}",
                    description=item.provider.business_name,
                    status_label="eligible",
                    timestamp=item.completed_at or item.updated_at,
                    href=f"/dashboard/services/bookings/{item.id}/review",
                )
                for item in eligible_reviews[:5]
            ],
        )

        data = {
            "stats": [
                {
                    "label": "Quote requests",
                    "value": str(quote_requests.count()),
                    "detail": "Requests sent to service providers",
                },
                {
                    "label": "Pending responses",
                    "value": str(
                        quote_requests.filter(
                            status__in=[QuoteRequestStatus.SUBMITTED, QuoteRequestStatus.VIEWED]
                        ).count()
                    ),
                    "detail": "Quotes not yet marked responded or closed",
                },
                {
                    "label": "Submitted reviews",
                    "value": str(submitted_reviews.count()),
                    "detail": "Reviews linked to completed engagements",
                },
                {
                    "label": "Reviews waiting",
                    "value": str(eligible_reviews.count()),
                    "detail": "Completed services still eligible for review",
                },
            ],
            "recent_quote_requests": quote_requests[:5],
            "submitted_reviews": submitted_reviews[:5],
            "eligible_reviews": eligible_reviews[:5],
            "recent_providers": recent_providers[:5],
            "recommended_providers": recommended_providers,
            "service_categories": categories,
            "activity": activity,
        }
        serializer = self.serializer_class(data, context={"request": request})
        return Response(serializer.data)


class ProviderServicesDashboardView(APIView):
    serializer_class = ProviderServicesDashboardSerializer
    permission_classes = [IsAuthenticated, IsEligibleServiceProvider]

    @extend_schema(responses={200: ProviderServicesDashboardSerializer})
    def get(self, request):
        provider = provider_queryset().filter(user=request.user).first()
        if not provider:
            data = {
                "profile": None,
                "stats": [
                    {
                        "label": "Profile completion",
                        "value": "0%",
                        "detail": "Create a provider profile to start tracking service operations",
                    }
                ],
                "quote_status_counts": count_by_status(
                    QuoteRequest.objects.none(),
                    QuoteRequestStatus,
                ),
                "review_status_counts": count_by_status(
                    ServiceReview.objects.none(),
                    ServiceReviewStatus,
                ),
                "recent_quote_requests": [],
                "latest_reviews": [],
                "response_reminders": [],
                "activity": [],
            }
            return Response(self.serializer_class(data, context={"request": request}).data)

        quotes = quote_request_queryset().filter(provider=provider)
        reviews = review_queryset().filter(provider=provider)
        bookings = ServiceBooking.objects.filter(provider=provider)
        completion = validate_provider_submission(provider)
        missing = completion.get("missing", [])
        total_completion_items = 6
        completion_percentage = round(
            ((total_completion_items - len(missing)) / total_completion_items) * 100
        )
        active_trades = provider.trades.filter(status=ProviderTradeStatus.ACTIVE).select_related(
            "category"
        )
        active_service_areas = provider.service_areas.all()
        portfolio_count = provider.portfolio_images.count()
        response_reminders = reviews.filter(
            status=ServiceReviewStatus.PUBLISHED,
            provider_response="",
        ).order_by("-published_at", "-created_at")

        activity = newest_activity(
            [
                activity_item(
                    item_id=f"quote-{item.id}",
                    title=f"New quote: {item.project_title}",
                    description=item.customer_name,
                    status_label=item.status,
                    timestamp=item.created_at,
                    href="/dashboard/artisan/quote-requests",
                )
                for item in quotes.order_by("-created_at")[:5]
            ],
            [
                activity_item(
                    item_id=f"review-{item.id}",
                    title=f"Review: {item.title}",
                    description=f"{item.rating}/5 from a verified customer",
                    status_label=item.status,
                    timestamp=item.created_at,
                    href="/dashboard/artisan/reviews",
                )
                for item in reviews.order_by("-created_at")[:5]
            ],
        )

        data = {
            "profile": provider,
            "stats": [
                {
                    "label": "Profile completion",
                    "value": f"{completion_percentage}%",
                    "detail": completion.get("message", ""),
                },
                {
                    "label": "Average rating",
                    "value": str(provider.average_rating),
                    "detail": f"{provider.published_review_count} published reviews",
                },
                {
                    "label": "Quote requests",
                    "value": str(quotes.count()),
                    "detail": "Total service enquiries received",
                },
                {
                    "label": "Completed jobs",
                    "value": str(
                        bookings.filter(status=ServiceBookingStatus.COMPLETED).count()
                    ),
                    "detail": "Completed service engagements",
                },
                {
                    "label": "Portfolio",
                    "value": str(portfolio_count),
                    "detail": "Public work samples",
                },
                {
                    "label": "Coverage",
                    "value": str(active_service_areas.count()),
                    "detail": "Service areas listed",
                },
                {
                    "label": "Primary trade",
                    "value": (
                        active_trades.filter(is_primary=True).first().category.name
                        if active_trades.filter(is_primary=True).exists()
                        else "Not set"
                    ),
                    "detail": f"{active_trades.count()} active trades",
                },
                {
                    "label": "Response reminders",
                    "value": str(response_reminders.count()),
                    "detail": "Published reviews awaiting a provider response",
                },
            ],
            "quote_status_counts": count_by_status(quotes, QuoteRequestStatus),
            "review_status_counts": count_by_status(reviews, ServiceReviewStatus),
            "recent_quote_requests": quotes.order_by("-created_at")[:5],
            "latest_reviews": reviews.order_by("-created_at")[:5],
            "response_reminders": response_reminders[:5],
            "activity": activity,
        }
        return Response(self.serializer_class(data, context={"request": request}).data)


class AdminServicesDashboardView(APIView):
    serializer_class = AdminServicesDashboardSerializer
    permission_classes = [IsAuthenticated, IsServicesAdmin]

    @extend_schema(responses={200: AdminServicesDashboardSerializer})
    def get(self, request):
        providers = provider_queryset()
        quotes = quote_request_queryset()
        reviews = review_queryset()
        pending_providers = providers.filter(
            status__in=[ProviderStatus.PENDING_REVIEW, ProviderStatus.NEEDS_MORE_INFORMATION]
        ).order_by("-submitted_at", "-created_at")
        pending_reviews = reviews.filter(status=ServiceReviewStatus.PENDING).order_by("-created_at")
        flagged_reviews = reviews.filter(status=ServiceReviewStatus.FLAGGED).order_by("-updated_at")
        open_quotes = quotes.exclude(
            status__in=[QuoteRequestStatus.CLOSED, QuoteRequestStatus.CANCELLED]
        ).order_by("-created_at")

        category_breakdown = [
            {"label": item["name"], "value": item["provider_count"]}
            for item in TradeCategory.objects.filter(is_active=True)
            .annotate(
                provider_count=Count(
                    "provider_trades__provider",
                    filter=Q(
                        provider_trades__status=ProviderTradeStatus.ACTIVE,
                        provider_trades__provider__status=ProviderStatus.ACTIVE,
                    ),
                    distinct=True,
                )
            )
            .filter(provider_count__gt=0)
            .order_by("-provider_count", "name")[:8]
            .values("name", "provider_count")
        ]
        geographic_breakdown = [
            {
                "label": ", ".join(part for part in [item["city"], item["state"]] if part),
                "value": item["provider_count"],
            }
            for item in ServiceArea.objects.values("state", "city")
            .annotate(provider_count=Count("provider", distinct=True))
            .order_by("-provider_count", "state", "city")[:8]
        ]

        activity = newest_activity(
            [
                activity_item(
                    item_id=f"provider-{item.id}",
                    title=f"Provider profile: {item.business_name}",
                    description=item.public_display_location,
                    status_label=item.status,
                    timestamp=item.submitted_at or item.created_at,
                    href=f"/admin/services/providers/{item.id}",
                )
                for item in pending_providers[:5]
            ],
            [
                activity_item(
                    item_id=f"review-{item.id}",
                    title=f"Review moderation: {item.title}",
                    description=item.provider.business_name,
                    status_label=item.status,
                    timestamp=item.updated_at,
                    href=f"/admin/services/reviews/{item.id}",
                )
                for item in reviews.order_by("-updated_at")[:5]
            ],
            [
                activity_item(
                    item_id=f"quote-{item.id}",
                    title=f"Quote request: {item.project_title}",
                    description=item.provider.business_name,
                    status_label=item.status,
                    timestamp=item.updated_at,
                    href="/admin/services/quote-requests",
                )
                for item in quotes.order_by("-updated_at")[:5]
            ],
        )
        average_rating = (
            providers.filter(
                status=ProviderStatus.ACTIVE,
                published_review_count__gt=0,
            ).aggregate(value=Avg("average_rating"))["value"]
            or 0
        )

        data = {
            "stats": [
                {
                    "label": "Pending provider approvals",
                    "value": str(pending_providers.count()),
                    "detail": "Profiles waiting for admin action",
                },
                {
                    "label": "Active providers",
                    "value": str(providers.filter(status=ProviderStatus.ACTIVE).count()),
                    "detail": "Visible in public services marketplace",
                },
                {
                    "label": "Open quote requests",
                    "value": str(open_quotes.count()),
                    "detail": "Submitted, viewed, or responded enquiries",
                },
                {
                    "label": "Pending reviews",
                    "value": str(pending_reviews.count()),
                    "detail": "Customer reviews waiting for moderation",
                },
                {
                    "label": "Flagged reviews",
                    "value": str(flagged_reviews.count()),
                    "detail": "Reviews needing trust review",
                },
                {
                    "label": "Average rating",
                    "value": f"{average_rating:.2f}",
                    "detail": "Average across active providers with published reviews",
                },
            ],
            "provider_status_counts": count_by_status(providers, ProviderStatus),
            "quote_status_counts": count_by_status(quotes, QuoteRequestStatus),
            "review_status_counts": count_by_status(reviews, ServiceReviewStatus),
            "pending_providers": pending_providers[:5],
            "pending_reviews": pending_reviews[:5],
            "flagged_reviews": flagged_reviews[:5],
            "open_quote_requests": open_quotes[:5],
            "category_breakdown": category_breakdown,
            "geographic_breakdown": geographic_breakdown,
            "activity": activity,
        }
        return Response(self.serializer_class(data, context={"request": request}).data)


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
        if response := self.ensure_provider_can_mutate(self.get_provider()):
            return response
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
        provider = self.get_provider()
        if response := self.ensure_provider_can_mutate(provider):
            return response
        serializer = PortfolioReorderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
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
    def warn(self, request, pk=None):
        provider = self.get_object()
        if response := self._ensure_not_self_review(provider):
            return response
        serializer = self._decision_serializer()
        reason = serializer.validated_data.get("reason", "").strip()
        if not reason:
            return Response({"reason": ["Warning reason is required."]}, status=400)
        provider.warn(reviewer=request.user, reason=reason)
        provider.review_notes = serializer.validated_data.get("review_notes", "")
        provider.save(update_fields=["review_notes", "updated_at"])
        emit_service_event(
            actor=request.user,
            action="service_provider.warned",
            entity=provider,
            metadata={"reason": reason, "warning_count": provider.warning_count},
        )
        return Response(self.get_serializer(provider).data)

    @action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        provider = self.get_object()
        if response := self._ensure_not_self_review(provider):
            return response
        serializer = self._decision_serializer()
        reason = serializer.validated_data.get("reason", "").strip()
        if not reason:
            return Response({"reason": ["Suspension reason is required."]}, status=400)
        suspension_type = serializer.validated_data.get(
            "suspension_type",
            ProviderSuspensionType.TEMPORARY,
        )
        expires_at = serializer.validated_data.get("suspension_expires_at")
        if suspension_type == ProviderSuspensionType.TEMPORARY and not expires_at:
            return Response(
                {"suspension_expires_at": ["Temporary suspensions require an expiry time."]},
                status=400,
            )
        if suspension_type == ProviderSuspensionType.PERMANENT:
            expires_at = None
        provider.suspend(
            reviewer=request.user,
            reason=reason,
            suspension_type=suspension_type,
            expires_at=expires_at,
        )
        provider.review_notes = serializer.validated_data.get("review_notes", "")
        provider.save(update_fields=["review_notes", "updated_at"])
        emit_service_event(
            actor=request.user,
            action="service_provider.suspended",
            entity=provider,
            metadata={
                "reason": reason,
                "suspension_type": suspension_type,
                "expires_at": expires_at.isoformat() if expires_at else "",
            },
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
        if quote_request.provider.status == ProviderStatus.SUSPENDED:
            return Response(
                {"detail": "Suspended providers cannot manage quote request status."},
                status=status.HTTP_403_FORBIDDEN,
            )
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
        if review.provider.status == ProviderStatus.SUSPENDED:
            return Response(
                {"detail": "Suspended providers cannot respond to reviews."},
                status=status.HTTP_403_FORBIDDEN,
            )
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
