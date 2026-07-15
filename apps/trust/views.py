"""API views for user and property verification workflows."""

from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.services import create_audit_log
from apps.trust.models import PropertyVerification, VerificationRequest
from apps.trust.permissions import IsPropertyVerificationSubmitter, IsVerificationRequestOwner
from apps.trust.serializers import (
    PropertyVerificationSerializer,
    VerificationDocumentSerializer,
    VerificationRequestSerializer,
)


class VerificationRequestViewSet(viewsets.ModelViewSet):
    """Self-service verification requests: submit, view, upload documents, resubmit.

    Users may only ever see and act on their own requests -- there is no
    list-all-users endpoint here by design, that lives in the admin view.
    """

    serializer_class = VerificationRequestSerializer
    permission_classes = [IsAuthenticated, IsVerificationRequestOwner]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return VerificationRequest.objects.filter(user=self.request.user).select_related("reviewer")

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
        create_audit_log(
            actor=request.user,
            action="property_verification_resubmitted",
            entity=property_verification,
            metadata={"previous_status": before_status},
        )
        return Response(
            PropertyVerificationSerializer(property_verification, context={"request": request}).data,
        )
