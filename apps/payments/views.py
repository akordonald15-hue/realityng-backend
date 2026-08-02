from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.services import user_is_admin
from apps.payments import services
from apps.payments.filters import (
    PaymentDisputeFilterSet,
    PaymentMilestoneFilterSet,
    TransactionFilterSet,
)
from apps.payments.models import PaymentDispute, PaymentMilestone, PaymentProof, Transaction
from apps.payments.permissions import (
    IsMilestoneParticipantOrAdmin,
    IsProofParticipantOrAdmin,
    IsReviewerOrAdmin,
    IsTransactionParticipantOrAdmin,
)
from apps.payments.serializers import (
    DisputeCreateSerializer,
    DisputeResolveSerializer,
    MilestoneCreateSerializer,
    PaymentDisputeSerializer,
    PaymentMilestoneSerializer,
    PaymentProofCreateSerializer,
    PaymentProofSerializer,
    TransactionSerializer,
)


def _error(exc: DjangoValidationError):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated, IsTransactionParticipantOrAdmin]
    filterset_class = TransactionFilterSet
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Transaction.objects.none()
        user = self.request.user
        qs = Transaction.objects.select_related("property", "buyer", "owner", "application")
        if user_is_admin(user):
            return qs
        return qs.filter(models_q_participant(user))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        txn = services.create_transaction(
            property=data["property"],
            buyer=data["buyer"],
            owner=data["owner"],
            actor=request.user,
            application=data.get("application"),
            currency=data.get("currency", "NGN"),
            notes=data.get("notes", ""),
        )
        output = self.get_serializer(txn)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="milestones")
    def milestones(self, request, pk=None):
        transaction = self.get_object()
        serializer = MilestoneCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        milestone = services.create_milestone(
            transaction=transaction, actor=request.user, **serializer.validated_data
        )
        return Response(PaymentMilestoneSerializer(milestone).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        txn = self.get_object()
        try:
            services.activate_transaction(txn, request.user)
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(self.get_serializer(txn).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        txn = self.get_object()
        try:
            services.complete_transaction(txn, request.user)
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(self.get_serializer(txn).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        txn = self.get_object()
        try:
            services.cancel_transaction(txn, request.user, reason=request.data.get("reason", ""))
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(self.get_serializer(txn).data)

    @action(detail=True, methods=["post"], url_path="dispute")
    def dispute(self, request, pk=None):
        txn = self.get_object()
        serializer = DisputeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dispute = services.open_dispute(
            transaction=txn, opened_by=request.user, **serializer.validated_data
        )
        return Response(PaymentDisputeSerializer(dispute).data, status=status.HTTP_201_CREATED)


def models_q_participant(user):
    from django.db.models import Q

    return Q(buyer=user) | Q(owner=user)


class PaymentMilestoneViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    serializer_class = PaymentMilestoneSerializer
    permission_classes = [IsAuthenticated, IsMilestoneParticipantOrAdmin]
    filterset_class = PaymentMilestoneFilterSet

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PaymentMilestone.objects.none()
        user = self.request.user
        qs = PaymentMilestone.objects.select_related("transaction").prefetch_related("proofs")
        if user_is_admin(user):
            return qs
        return qs.filter(models_q_participant_milestone(user))

    @action(
        detail=True, methods=["post"], url_path="proofs",
        parser_classes=[MultiPartParser, FormParser],
    )
    def proofs(self, request, pk=None):
        milestone = self.get_object()
        serializer = PaymentProofCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            proof = services.submit_payment_proof(
                milestone=milestone, uploaded_by=request.user, **serializer.validated_data
            )
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(PaymentProofSerializer(proof).data, status=status.HTTP_201_CREATED)

    @action(
        detail=True, methods=["post"], url_path="start-review",
        permission_classes=[IsAuthenticated, IsReviewerOrAdmin],
    )
    def start_review(self, request, pk=None):
        milestone = self.get_object()
        try:
            services.start_milestone_review(milestone, request.user)
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(self.get_serializer(milestone).data)

    @action(
        detail=True, methods=["post"], url_path="accept",
        permission_classes=[IsAuthenticated, IsReviewerOrAdmin],
    )
    def accept(self, request, pk=None):
        milestone = self.get_object()
        try:
            services.accept_milestone(milestone, request.user, note=request.data.get("note", ""))
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(self.get_serializer(milestone).data)

    @action(
        detail=True, methods=["post"], url_path="reject",
        permission_classes=[IsAuthenticated, IsReviewerOrAdmin],
    )
    def reject(self, request, pk=None):
        milestone = self.get_object()
        try:
            services.reject_milestone(milestone, request.user, note=request.data.get("note", ""))
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(self.get_serializer(milestone).data)

    @action(detail=True, methods=["post"], url_path="dispute")
    def dispute(self, request, pk=None):
        milestone = self.get_object()
        reason = request.data.get("reason", "")
        dispute = services.open_dispute(
            transaction=milestone.transaction,
            opened_by=request.user,
            reason=reason,
            milestone=milestone,
        )
        return Response(PaymentDisputeSerializer(dispute).data, status=status.HTTP_201_CREATED)


def models_q_participant_milestone(user):
    from django.db.models import Q

    return Q(transaction__buyer=user) | Q(transaction__owner=user)


class PaymentProofViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = PaymentProofSerializer
    permission_classes = [IsAuthenticated, IsProofParticipantOrAdmin]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PaymentProof.objects.none()
        user = self.request.user
        qs = PaymentProof.objects.select_related("milestone__transaction")
        if user_is_admin(user):
            return qs
        return qs.filter(models_q_participant_proof(user))

    @action(detail=True, methods=["get"], url_path="signed-url")
    def signed_url(self, request, pk=None):
        proof = self.get_object()
        url = proof.file.storage.url(proof.file.name)
        return Response({"url": url})


def models_q_participant_proof(user):
    from django.db.models import Q

    return Q(milestone__transaction__buyer=user) | Q(milestone__transaction__owner=user)


class PaymentDisputeViewSet(
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    serializer_class = PaymentDisputeSerializer
    permission_classes = [IsAuthenticated, IsTransactionParticipantOrAdmin]
    filterset_class = PaymentDisputeFilterSet

    def get_object(self):
        obj = super().get_object()
        self.check_object_permissions(self.request, obj.transaction)
        return obj

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PaymentDispute.objects.none()
        user = self.request.user
        qs = PaymentDispute.objects.select_related("transaction", "milestone")
        if user_is_admin(user):
            return qs
        return qs.filter(models_q_dispute(user))

    @action(
        detail=True, methods=["post"], url_path="resolve",
        permission_classes=[IsAuthenticated],
    )
    def resolve(self, request, pk=None):
        dispute = self.get_object()
        if not (dispute.transaction.owner_id == request.user.id or user_is_admin(request.user)):
            return Response(
                {"detail": "Only the property owner or an admin can resolve disputes."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = DisputeResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dispute = services.resolve_dispute(dispute, request.user, **serializer.validated_data)
        return Response(self.get_serializer(dispute).data)


def models_q_dispute(user):
    from django.db.models import Q

    return Q(transaction__buyer=user) | Q(transaction__owner=user)
