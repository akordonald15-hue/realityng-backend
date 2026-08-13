from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle

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
    can_manage_transaction,
)
from apps.payments.serializers import (
    DisputeCreateSerializer,
    DisputeResolveSerializer,
    MilestoneCreateSerializer,
    PaymentDisputeSerializer,
    PaymentMilestoneSerializer,
    PaymentProofCreateSerializer,
    PaymentProofSerializer,
    TransactionCreateSerializer,
    TransactionSerializer,
)
from apps.properties.choices import PropertyAssignmentCapability
from apps.properties.services import property_ids_for_user_capability, user_has_property_capability


def _error(exc: DjangoValidationError):
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def _can_manage_property_payment(user, prop) -> bool:
    if user_is_admin(user) or prop.owner_id == user.id:
        return True
    return user_has_property_capability(
        user,
        prop,
        PropertyAssignmentCapability.MANAGE_LISTING,
    )


def _manageable_property_ids(user):
    return property_ids_for_user_capability(
        user,
        PropertyAssignmentCapability.MANAGE_LISTING,
    )


class ActionScopedThrottleMixin:
    throttle_scope_by_action: dict[str, str] = {}
    throttle_classes = [AnonRateThrottle, UserRateThrottle, ScopedRateThrottle]

    def get_throttles(self):
        if getattr(self, "action", None) in self.throttle_scope_by_action:
            self.throttle_scope = self.throttle_scope_by_action[self.action]
        return super().get_throttles()


class TransactionViewSet(ActionScopedThrottleMixin, viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated, IsTransactionParticipantOrAdmin]
    filterset_class = TransactionFilterSet
    http_method_names = ["get", "post", "head", "options"]
    throttle_scope_by_action = {"create": "payment_transaction_create"}

    def get_serializer_class(self):
        if self.action == "create":
            return TransactionCreateSerializer
        return TransactionSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Transaction.objects.none()
        user = self.request.user
        qs = Transaction.objects.select_related(
            "property",
            "buyer",
            "owner",
            "application",
        ).prefetch_related(
            "milestones",
            "milestones__proofs",
            "disputes",
        )
        if user_is_admin(user):
            return qs
        manageable_property_ids = _manageable_property_ids(user)
        return qs.filter(models_q_participant(user) | Q(property_id__in=manageable_property_ids))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        prop = serializer.context["property"]
        application = serializer.context.get("application")
        buyer = serializer.context["buyer"]
        owner = serializer.context["owner"]
        if application and not _can_manage_property_payment(request.user, prop):
            return Response(
                {
                    "detail": (
                        "Only the property owner or an assigned manager can create this "
                        "transaction."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if not application and request.user.id != buyer.id:
            return Response(
                {"detail": "You can only create your own transaction records."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            txn = services.create_transaction(
                property=prop,
                buyer=buyer,
                owner=owner,
                actor=request.user,
                application=application,
                currency=data.get("currency", "NGN"),
                notes=data.get("notes", ""),
            )
        except DjangoValidationError as exc:
            return _error(exc)
        output = TransactionSerializer(txn, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="milestones")
    def milestones(self, request, pk=None):
        transaction = self.get_object()
        if not can_manage_transaction(request.user, transaction):
            return Response(
                {"detail": "Only the property owner or an assigned manager can create milestones."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = MilestoneCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        milestone = services.create_milestone(
            transaction=transaction, actor=request.user, **serializer.validated_data
        )
        return Response(PaymentMilestoneSerializer(milestone).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        txn = self.get_object()
        if not can_manage_transaction(request.user, txn):
            return Response(
                {
                    "detail": (
                        "Only the property owner or an assigned manager can activate "
                        "transactions."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            services.activate_transaction(txn, request.user)
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(self.get_serializer(txn).data)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        txn = self.get_object()
        if not can_manage_transaction(request.user, txn):
            return Response(
                {
                    "detail": (
                        "Only the property owner or an assigned manager can complete "
                        "transactions."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            services.complete_transaction(txn, request.user)
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(self.get_serializer(txn).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        txn = self.get_object()
        if not can_manage_transaction(request.user, txn):
            return Response(
                {
                    "detail": (
                        "Only the property owner or an assigned manager can cancel "
                        "transactions."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
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
        try:
            dispute = services.open_dispute(
                transaction=txn, opened_by=request.user, **serializer.validated_data
            )
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(PaymentDisputeSerializer(dispute).data, status=status.HTTP_201_CREATED)


def models_q_participant(user):
    return Q(buyer=user) | Q(owner=user)


class PaymentMilestoneViewSet(
    ActionScopedThrottleMixin,
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    serializer_class = PaymentMilestoneSerializer
    permission_classes = [IsAuthenticated, IsMilestoneParticipantOrAdmin]
    filterset_class = PaymentMilestoneFilterSet
    throttle_scope_by_action = {
        "proofs": "payment_proof_upload",
        "dispute": "payment_dispute_create",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PaymentMilestone.objects.none()
        user = self.request.user
        qs = PaymentMilestone.objects.select_related("transaction").prefetch_related("proofs")
        if user_is_admin(user):
            return qs
        manageable_property_ids = _manageable_property_ids(user)
        return qs.filter(
            models_q_participant_milestone(user)
            | Q(transaction__property_id__in=manageable_property_ids)
        )

    @action(
        detail=True, methods=["post"], url_path="proofs",
        parser_classes=[MultiPartParser, FormParser],
    )
    def proofs(self, request, pk=None):
        milestone = self.get_object()
        if request.user.id != milestone.transaction.buyer_id and not user_is_admin(request.user):
            return Response(
                {"detail": "Only the buyer can submit payment proof."},
                status=status.HTTP_403_FORBIDDEN,
            )
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
        try:
            dispute = services.open_dispute(
                transaction=milestone.transaction,
                opened_by=request.user,
                reason=reason,
                milestone=milestone,
            )
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(PaymentDisputeSerializer(dispute).data, status=status.HTTP_201_CREATED)


def models_q_participant_milestone(user):
    return Q(transaction__buyer=user) | Q(transaction__owner=user)


class PaymentProofViewSet(
    ActionScopedThrottleMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PaymentProofSerializer
    permission_classes = [IsAuthenticated, IsProofParticipantOrAdmin]
    throttle_scope_by_action = {"signed_url": "payment_signed_url"}

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return PaymentProof.objects.none()
        user = self.request.user
        qs = PaymentProof.objects.select_related("milestone__transaction")
        if user_is_admin(user):
            return qs
        manageable_property_ids = _manageable_property_ids(user)
        return qs.filter(
            models_q_participant_proof(user)
            | Q(milestone__transaction__property_id__in=manageable_property_ids)
        )

    @action(detail=True, methods=["get"], url_path="signed-url")
    def signed_url(self, request, pk=None):
        proof = self.get_object()
        url = proof.file.storage.url(proof.file.name)
        return Response({"url": url})


def models_q_participant_proof(user):
    return Q(milestone__transaction__buyer=user) | Q(milestone__transaction__owner=user)


class PaymentDisputeViewSet(
    ActionScopedThrottleMixin,
    mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    serializer_class = PaymentDisputeSerializer
    permission_classes = [IsAuthenticated, IsTransactionParticipantOrAdmin]
    filterset_class = PaymentDisputeFilterSet
    throttle_scope_by_action = {"resolve": "payment_dispute_create"}

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
        manageable_property_ids = _manageable_property_ids(user)
        return qs.filter(
            models_q_dispute(user) | Q(transaction__property_id__in=manageable_property_ids)
        )

    @action(
        detail=True, methods=["post"], url_path="resolve",
        permission_classes=[IsAuthenticated],
    )
    def resolve(self, request, pk=None):
        dispute = self.get_object()
        if not can_manage_transaction(request.user, dispute.transaction):
            return Response(
                {
                    "detail": (
                        "Only the property owner, assigned manager, or admin can resolve "
                        "disputes."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = DisputeResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dispute = services.resolve_dispute(dispute, request.user, **serializer.validated_data)
        return Response(self.get_serializer(dispute).data)


def models_q_dispute(user):
    return Q(transaction__buyer=user) | Q(transaction__owner=user)
