from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle

from apps.accounts.services import user_is_admin
from apps.construction.models import ConstructionMilestone
from apps.inspections.models import InspectionRequest
from apps.payments import services
from apps.payments.filters import (
    EscrowTransactionFilterSet,
    PaymentDisputeFilterSet,
    PaymentMilestoneFilterSet,
    TransactionFilterSet,
)
from apps.payments.models import (
    EscrowCondition,
    EscrowProvider,
    EscrowRefund,
    EscrowRelease,
    EscrowTransaction,
    PaymentDispute,
    PaymentMilestone,
    PaymentProof,
    Transaction,
)
from apps.payments.permissions import (
    IsEscrowParticipantOrAdmin,
    IsMilestoneParticipantOrAdmin,
    IsProofParticipantOrAdmin,
    IsReviewerOrAdmin,
    IsTransactionParticipantOrAdmin,
    can_manage_transaction,
)
from apps.payments.serializers import (
    DisputeCreateSerializer,
    DisputeResolveSerializer,
    EscrowConditionCreateSerializer,
    EscrowConditionSatisfySerializer,
    EscrowConditionSerializer,
    EscrowCreateSerializer,
    EscrowFundingEventSerializer,
    EscrowProviderSerializer,
    EscrowReconcileSerializer,
    EscrowReconciliationRecordSerializer,
    EscrowRefundApproveSerializer,
    EscrowRefundConfirmSerializer,
    EscrowRefundRequestSerializer,
    EscrowRefundSerializer,
    EscrowReleaseApproveSerializer,
    EscrowReleaseConfirmSerializer,
    EscrowReleaseRequestSerializer,
    EscrowReleaseSerializer,
    EscrowSettlementRecordSerializer,
    EscrowSettlementSerializer,
    EscrowTransactionSerializer,
    MilestoneCreateSerializer,
    PaymentDisputeSerializer,
    PaymentMilestoneSerializer,
    PaymentProofCreateSerializer,
    PaymentProofSerializer,
    ProviderWebhookEventSerializer,
    RecordFundingSerializer,
    RecordProviderReferenceSerializer,
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


def _escrow_manageable_property_ids(user):
    return property_ids_for_user_capability(
        user,
        PropertyAssignmentCapability.MANAGE_TRANSACTIONS,
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

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="escrow",
        throttle_classes=[AnonRateThrottle, UserRateThrottle, ScopedRateThrottle],
    )
    def escrow(self, request, pk=None):
        txn = self.get_object()
        if request.method.lower() == "get":
            try:
                escrow = txn.escrow
            except EscrowTransaction.DoesNotExist:
                return Response({"detail": "Escrow has not been started."}, status=404)
            return Response(EscrowTransactionSerializer(escrow).data)
        self.throttle_scope = "escrow_create"
        serializer = EscrowCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            provider = EscrowProvider.objects.get(id=serializer.validated_data["provider_id"])
            escrow = services.create_escrow_transaction(
                transaction=txn,
                provider=provider,
                actor=request.user,
                **{
                    key: value
                    for key, value in serializer.validated_data.items()
                    if key != "provider_id"
                },
            )
        except (EscrowProvider.DoesNotExist, DjangoValidationError) as exc:
            return _error(exc)
        return Response(EscrowTransactionSerializer(escrow).data, status=status.HTTP_201_CREATED)


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


class EscrowProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EscrowProviderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return EscrowProvider.objects.none()
        if user_is_admin(self.request.user):
            return EscrowProvider.objects.all()
        return EscrowProvider.objects.filter(status__in=["active", "sandbox"])


class EscrowTransactionViewSet(ActionScopedThrottleMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = EscrowTransactionSerializer
    permission_classes = [IsAuthenticated, IsEscrowParticipantOrAdmin]
    filterset_class = EscrowTransactionFilterSet
    throttle_scope_by_action = {
        "request_release": "escrow_release_request",
        "request_refund": "escrow_refund_request",
        "record_funding": "escrow_admin_action",
        "record_provider_reference": "escrow_admin_action",
        "approve_release": "escrow_admin_action",
        "confirm_release": "escrow_admin_action",
        "approve_refund": "escrow_admin_action",
        "confirm_refund": "escrow_admin_action",
        "record_settlement": "escrow_admin_action",
        "reconcile": "escrow_reconcile",
    }

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return EscrowTransaction.objects.none()
        qs = EscrowTransaction.objects.select_related(
            "transaction",
            "transaction__property",
            "transaction__buyer",
            "transaction__owner",
            "provider",
            "created_by",
        ).prefetch_related(
            "funding_events",
            "conditions",
            "releases",
            "refunds",
            "settlements",
            "settlements__allocations",
            "reconciliation_records",
        )
        user = self.request.user
        if user_is_admin(user):
            return qs
        manageable_property_ids = _escrow_manageable_property_ids(user)
        return qs.filter(
            Q(transaction__buyer=user)
            | Q(transaction__owner=user)
            | Q(transaction__property_id__in=manageable_property_ids)
        )

    def _require_manager(self, escrow: EscrowTransaction):
        if not services.can_manage_escrow(self.request.user, escrow.transaction):
            return Response({"detail": "You are not allowed to manage this escrow."}, status=403)
        return None

    @action(detail=True, methods=["post"], url_path="record-provider-reference")
    def record_provider_reference(self, request, pk=None):
        escrow = self.get_object()
        if denied := self._require_manager(escrow):
            return denied
        serializer = RecordProviderReferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            escrow = services.record_provider_reference(
                escrow=escrow,
                actor=request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(self.get_serializer(escrow).data)

    @action(detail=True, methods=["post"], url_path="record-funding")
    def record_funding(self, request, pk=None):
        escrow = self.get_object()
        if denied := self._require_manager(escrow):
            return denied
        serializer = RecordFundingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            funding_event, _created = services.record_funding_event(
                escrow=escrow,
                actor=request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(
            EscrowFundingEventSerializer(funding_event).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="conditions")
    def conditions(self, request, pk=None):
        escrow = self.get_object()
        if denied := self._require_manager(escrow):
            return denied
        serializer = EscrowConditionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            inspection_request = None
            construction_milestone = None
            if data.get("inspection_request"):
                inspection_request = InspectionRequest.objects.get(id=data["inspection_request"])
            if data.get("construction_milestone"):
                construction_milestone = ConstructionMilestone.objects.get(
                    id=data["construction_milestone"]
                )
            condition = services.create_escrow_condition(
                escrow=escrow,
                actor=request.user,
                condition_type=data["condition_type"],
                description=data.get("description", ""),
                required=data.get("required", True),
                inspection_request=inspection_request,
                construction_milestone=construction_milestone,
            )
        except (
            DjangoValidationError,
            InspectionRequest.DoesNotExist,
            ConstructionMilestone.DoesNotExist,
        ) as exc:
            return _error(exc)
        return Response(EscrowConditionSerializer(condition).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="satisfy-condition")
    def satisfy_condition(self, request, pk=None):
        escrow = self.get_object()
        if denied := self._require_manager(escrow):
            return denied
        serializer = EscrowConditionSatisfySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            condition = EscrowCondition.objects.get(
                id=serializer.validated_data["condition_id"],
                escrow=escrow,
            )
            condition = services.satisfy_escrow_condition(
                condition=condition,
                actor=request.user,
                note=serializer.validated_data.get("note", ""),
            )
        except (EscrowCondition.DoesNotExist, DjangoValidationError) as exc:
            return _error(exc)
        return Response(EscrowConditionSerializer(condition).data)

    @action(detail=True, methods=["post"], url_path="request-release")
    def request_release(self, request, pk=None):
        escrow = self.get_object()
        serializer = EscrowReleaseRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            release = services.request_release(
                escrow=escrow,
                actor=request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(EscrowReleaseSerializer(release).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="approve-release")
    def approve_release(self, request, pk=None):
        escrow = self.get_object()
        if denied := self._require_manager(escrow):
            return denied
        serializer = EscrowReleaseApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            release = EscrowRelease.objects.get(
                id=serializer.validated_data["release_id"],
                escrow=escrow,
            )
            release = services.approve_release(
                release=release,
                actor=request.user,
                provider_instruction_id=serializer.validated_data.get(
                    "provider_instruction_id",
                    "",
                ),
                note=serializer.validated_data.get("note", ""),
            )
        except (EscrowRelease.DoesNotExist, DjangoValidationError) as exc:
            return _error(exc)
        return Response(EscrowReleaseSerializer(release).data)

    @action(detail=True, methods=["post"], url_path="confirm-release")
    def confirm_release(self, request, pk=None):
        escrow = self.get_object()
        if denied := self._require_manager(escrow):
            return denied
        serializer = EscrowReleaseConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            release = EscrowRelease.objects.get(
                id=serializer.validated_data["release_id"],
                escrow=escrow,
            )
            release = services.confirm_release(
                release=release,
                actor=request.user,
                provider_reference=serializer.validated_data["provider_reference"],
            )
        except (EscrowRelease.DoesNotExist, DjangoValidationError) as exc:
            return _error(exc)
        return Response(EscrowReleaseSerializer(release).data)

    @action(detail=True, methods=["post"], url_path="request-refund")
    def request_refund(self, request, pk=None):
        escrow = self.get_object()
        serializer = EscrowRefundRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refund = services.request_refund(
                escrow=escrow,
                actor=request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(EscrowRefundSerializer(refund).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="approve-refund")
    def approve_refund(self, request, pk=None):
        escrow = self.get_object()
        if denied := self._require_manager(escrow):
            return denied
        serializer = EscrowRefundApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refund = EscrowRefund.objects.get(
                id=serializer.validated_data["refund_id"],
                escrow=escrow,
            )
            refund = services.approve_refund(
                refund=refund,
                actor=request.user,
                provider_instruction_id=serializer.validated_data.get(
                    "provider_instruction_id",
                    "",
                ),
                note=serializer.validated_data.get("note", ""),
            )
        except (EscrowRefund.DoesNotExist, DjangoValidationError) as exc:
            return _error(exc)
        return Response(EscrowRefundSerializer(refund).data)

    @action(detail=True, methods=["post"], url_path="confirm-refund")
    def confirm_refund(self, request, pk=None):
        escrow = self.get_object()
        if denied := self._require_manager(escrow):
            return denied
        serializer = EscrowRefundConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refund = EscrowRefund.objects.get(
                id=serializer.validated_data["refund_id"],
                escrow=escrow,
            )
            refund = services.confirm_refund(
                refund=refund,
                actor=request.user,
                provider_reference=serializer.validated_data["provider_reference"],
            )
        except (EscrowRefund.DoesNotExist, DjangoValidationError) as exc:
            return _error(exc)
        return Response(EscrowRefundSerializer(refund).data)

    @action(detail=True, methods=["post"], url_path="record-settlement")
    def record_settlement(self, request, pk=None):
        escrow = self.get_object()
        if denied := self._require_manager(escrow):
            return denied
        serializer = EscrowSettlementRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            settlement = services.record_settlement(
                escrow=escrow,
                actor=request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(EscrowSettlementSerializer(settlement).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="reconcile")
    def reconcile(self, request, pk=None):
        escrow = self.get_object()
        if denied := self._require_manager(escrow):
            return denied
        serializer = EscrowReconcileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            record = services.reconcile_escrow(
                escrow=escrow,
                actor=request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            return _error(exc)
        return Response(
            EscrowReconciliationRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


class EscrowWebhookViewSet(ActionScopedThrottleMixin, viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = ProviderWebhookEventSerializer
    throttle_scope_by_action = {"receive": "escrow_webhook"}

    @action(detail=False, methods=["post"], url_path=r"(?P<provider_slug>[-\w]+)")
    def receive(self, request, provider_slug=None):
        try:
            provider = EscrowProvider.objects.get(slug=provider_slug)
            raw_body = request.body
            payload = request.data
            related_escrow = None
            escrow_id = payload.get("escrow_id")
            if escrow_id:
                related_escrow = EscrowTransaction.objects.filter(id=escrow_id).first()
            event, _created = services.record_provider_webhook(
                provider=provider,
                body=raw_body,
                signature=request.headers.get("X-RealityNG-Escrow-Signature"),
                provider_event_id=payload.get("provider_event_id", ""),
                event_type=payload.get("event_type", "unknown"),
                related_escrow=related_escrow,
            )
        except (EscrowProvider.DoesNotExist, DjangoValidationError) as exc:
            return _error(exc)
        if event.signature_status == "invalid":
            return Response({"detail": "Invalid provider webhook signature."}, status=400)
        return Response(ProviderWebhookEventSerializer(event).data, status=status.HTTP_202_ACCEPTED)
