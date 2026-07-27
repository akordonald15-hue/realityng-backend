"""API views for user, property, and admin verification workflows."""

from __future__ import annotations

from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.accounts.services import create_audit_log
from apps.trust.models import PropertyVerification, VerificationRequest
from apps.trust.permissions import IsPropertyVerificationSubmitter, IsVerificationRequestOwner
from apps.trust.serializers import (
    AdminPropertyVerificationSerializer,
    AdminVerificationRequestSerializer,
    PropertyVerificationSerializer,
    VerificationDecisionSerializer,
    VerificationDocumentSerializer,
    VerificationRequestSerializer,
)
from apps.trust.services import decide_property_verification_request, decide_verification_request

# ---------------------------------------------------------------------------
# Self-service (user-facing)
# ---------------------------------------------------------------------------


class VerificationRequestViewSet(viewsets.ModelViewSet):
    """Self-service verification requests: submit, view, upload documents, resubmit.

    Users may only ever see and act on their own requests -- listing all
    users' requests lives in the admin views below, not here.
    """

    serializer_class = VerificationRequestSerializer
    permission_classes = [IsAuthenticated, IsVerificationRequestOwner]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return VerificationRequest.objects.filter(user=self.request.user).select_related("reviewer")

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {"detail": "You already have an active verification request of this type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def perform_create(self, serializer) -> None:
        verification_request = serializer.save(status="pending")
        create_audit_log(
            actor=self.request.user,
            action="verification_submitted",
            entity=verification_request,
            metadata={"verification_type": verification_request.verification_type},
        )

    @action(detail=True, methods=["post"], url_path="documents")
    def documents(self, request, pk=None):
        verification_request = self.get_object()
        serializer = VerificationDocumentSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        document = serializer.save(verification_request=verification_request)
        create_audit_log(
            actor=request.user,
            action="verification_document_uploaded",
            entity=verification_request,
            metadata={"document_type": document.document_type, "document_id": str(document.id)},
        )
        return Response(
            VerificationDocumentSerializer(document, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="resubmit")
    def resubmit(self, request, pk=None):
        verification_request = self.get_object()
        if not verification_request.can_transition_to("pending"):
            return Response(
                {"detail": f"Cannot resubmit from status '{verification_request.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        before_status = verification_request.status
        verification_request.transition_to("pending")
        verification_request.submitted_at = timezone.now()
        verification_request.save(update_fields=["submitted_at", "updated_at"])
        create_audit_log(
            actor=request.user,
            action="verification_resubmitted",
            entity=verification_request,
            metadata={"previous_status": before_status},
        )
        return Response(
            VerificationRequestSerializer(verification_request, context={"request": request}).data,
        )


class PropertyVerificationViewSet(viewsets.ModelViewSet):
    """Self-service property verification: submit, view status, resubmit."""

    serializer_class = PropertyVerificationSerializer
    permission_classes = [IsAuthenticated, IsPropertyVerificationSubmitter]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return PropertyVerification.objects.filter(
            submitted_by=self.request.user
        ).select_related("property", "reviewer")

    def perform_create(self, serializer) -> None:
        property_verification = serializer.save(status="pending")
        create_audit_log(
            actor=self.request.user,
            action="property_verification_submitted",
            entity=property_verification,
            metadata={"property_id": str(property_verification.property_id)},
        )

    @action(detail=True, methods=["post"], url_path="resubmit")
    def resubmit(self, request, pk=None):
        property_verification = self.get_object()
        if not property_verification.can_transition_to("pending"):
            return Response(
                {"detail": f"Cannot resubmit from status '{property_verification.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        before_status = property_verification.status
        property_verification.transition_to("pending")
        property_verification.submitted_at = timezone.now()
        property_verification.save(update_fields=["submitted_at", "updated_at"])
        create_audit_log(
            actor=request.user,
            action="property_verification_resubmitted",
            entity=property_verification,
            metadata={"previous_status": before_status},
        )
        return Response(
            PropertyVerificationSerializer(
                property_verification,
                context={"request": request},
            ).data,
        )

    @action(detail=True, methods=["post"], url_path="documents")
    def documents(self, request, pk=None):
        property_verification = self.get_object()
        serializer = VerificationDocumentSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        document = serializer.save(property_verification=property_verification)
        create_audit_log(
            actor=request.user,
            action="property_verification_document_uploaded",
            entity=property_verification,
            metadata={
                "document_type": document.document_type,
                "document_id": str(document.id),
            },
        )
        return Response(
            VerificationDocumentSerializer(document, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Admin (review queue)
# ---------------------------------------------------------------------------


class AdminVerificationListView(generics.ListAPIView):
    """Admin queue listing, filterable by verification_type and status."""

    serializer_class = AdminVerificationRequestSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ["verification_type", "status"]
    queryset = VerificationRequest.objects.select_related("user", "reviewer").order_by(
        "-created_at"
    )


class AdminVerificationDetailView(generics.RetrieveAPIView):
    serializer_class = AdminVerificationRequestSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = VerificationRequest.objects.select_related("user", "reviewer")


class BaseVerificationDecisionView(APIView):
    """Shared body for every admin verification decision action.

    Subclasses set target_status; decide_verification_request() handles
    self-review blocking, transition validation, and audit logging.
    Not duplicated per action, unlike the accounts app's role-decision
    views, since the logic here is identical across five decision types.
    """

    permission_classes = [IsAuthenticated, IsAdmin]
    target_status: str = ""

    def post(self, request, pk):
        verification_request = get_object_or_404(VerificationRequest, pk=pk)
        serializer = VerificationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            decided = decide_verification_request(
                actor=request.user,
                verification_request=verification_request,
                status=self.target_status,
                **serializer.validated_data,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            AdminVerificationRequestSerializer(decided, context={"request": request}).data
        )


class AdminVerificationApproveView(BaseVerificationDecisionView):
    target_status = "approved"


class AdminVerificationRejectView(BaseVerificationDecisionView):
    target_status = "rejected"


class AdminVerificationRequestInfoView(BaseVerificationDecisionView):
    target_status = "needs_more_information"


class AdminVerificationSuspendView(BaseVerificationDecisionView):
    target_status = "suspended"


class AdminVerificationExpireView(BaseVerificationDecisionView):
    target_status = "expired"


class AdminPropertyVerificationListView(generics.ListAPIView):
    serializer_class = AdminPropertyVerificationSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ["status"]
    queryset = PropertyVerification.objects.select_related(
        "property", "submitted_by", "reviewer"
    ).order_by("-created_at")


class AdminPropertyVerificationDetailView(generics.RetrieveAPIView):
    serializer_class = AdminPropertyVerificationSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = PropertyVerification.objects.select_related("property", "submitted_by", "reviewer")


class BasePropertyVerificationDecisionView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    target_status: str = ""

    def post(self, request, pk):
        property_verification = get_object_or_404(PropertyVerification, pk=pk)
        serializer = VerificationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            decided = decide_property_verification_request(
                actor=request.user,
                property_verification=property_verification,
                status=self.target_status,
                rejection_reason=serializer.validated_data.get("rejection_reason", ""),
                expiry_date=serializer.validated_data.get("expiry_date"),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            AdminPropertyVerificationSerializer(decided, context={"request": request}).data
        )


class AdminPropertyVerificationApproveView(BasePropertyVerificationDecisionView):
    target_status = "approved"


class AdminPropertyVerificationRejectView(BasePropertyVerificationDecisionView):
    target_status = "rejected"


class AdminPropertyVerificationRequestInfoView(BasePropertyVerificationDecisionView):
    target_status = "needs_more_information"


class AdminPropertyVerificationSuspendView(BasePropertyVerificationDecisionView):
    target_status = "suspended"


class AdminPropertyVerificationExpireView(BasePropertyVerificationDecisionView):
    target_status = "expired"
