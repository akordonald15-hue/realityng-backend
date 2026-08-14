from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.payments import services
from apps.payments.choices import (
    DisputeStatus,
    EscrowConditionType,
    EscrowFeeType,
    EscrowFundingEventType,
    EscrowFundingStatus,
    EscrowProviderStatus,
    EscrowReconciliationStatus,
    EscrowRefundStatus,
    EscrowReleaseStatus,
    EscrowStatus,
)
from apps.payments.models import (
    EscrowFundingEvent,
    EscrowProvider,
    EscrowTransaction,
)
from apps.properties.choices import (
    PropertyAssignmentCapability,
    PropertyAssignmentStatus,
    PropertyAssignmentType,
)
from apps.properties.models import PropertyAssignment

pytestmark = pytest.mark.django_db


def authenticate(api_client, user):
    api_client.force_authenticate(user=user)


@pytest.fixture
def escrow_provider(db):
    return EscrowProvider.objects.create(
        name="Manual Escrow Partner",
        slug="manual-escrow",
        status=EscrowProviderStatus.ACTIVE,
        integration_mode="manual",
        supports_partial_funding=True,
        supports_partial_release=True,
        supported_currencies=["NGN", "USD"],
    )


@pytest.fixture
def escrow(transaction, escrow_provider, buyer):
    return services.create_escrow_transaction(
        transaction=transaction,
        provider=escrow_provider,
        actor=buyer,
        expected_amount=Decimal("1000000.00"),
        platform_fee_type=EscrowFeeType.PERCENTAGE,
        platform_fee_value=Decimal("1.00"),
    )


def test_create_escrow_attaches_to_existing_transaction(transaction, escrow_provider, buyer):
    escrow = services.create_escrow_transaction(
        transaction=transaction,
        provider=escrow_provider,
        actor=buyer,
        expected_amount=Decimal("100000000.00"),
        platform_fee_type=EscrowFeeType.PERCENTAGE,
        platform_fee_value=Decimal("1.00"),
    )

    assert escrow.transaction_id == transaction.id
    assert escrow.status == EscrowStatus.AWAITING_FUNDING
    assert escrow.expected_platform_fee == Decimal("1000000.00")
    assert escrow.confirmed_funded_amount == Decimal("0.00")


def test_duplicate_escrow_creation_returns_existing(transaction, escrow_provider, buyer):
    first = services.create_escrow_transaction(
        transaction=transaction,
        provider=escrow_provider,
        actor=buyer,
        expected_amount=Decimal("1000000.00"),
    )
    second = services.create_escrow_transaction(
        transaction=transaction,
        provider=escrow_provider,
        actor=buyer,
        expected_amount=Decimal("1000000.00"),
    )

    assert second.id == first.id
    assert EscrowTransaction.objects.count() == 1


def test_frontend_cannot_self_assert_funding(api_client, escrow, buyer):
    authenticate(api_client, buyer)

    response = api_client.post(
        f"/api/v1/payment-escrows/{escrow.id}/record-funding/",
        {
            "provider_event_id": "evt-client",
            "amount": "1000000.00",
            "currency": "NGN",
        },
        format="json",
    )

    assert response.status_code == 403
    escrow.refresh_from_db()
    assert escrow.confirmed_funded_amount == Decimal("0.00")
    assert escrow.funding_status == EscrowFundingStatus.FUNDING_EXPECTED


def test_owner_records_partial_and_full_provider_funding(api_client, escrow, owner):
    authenticate(api_client, owner)

    response = api_client.post(
        f"/api/v1/payment-escrows/{escrow.id}/record-funding/",
        {
            "provider_event_id": "evt-partial",
            "amount": "400000.00",
            "currency": "NGN",
            "event_type": EscrowFundingEventType.PARTIAL_FUNDING_CONFIRMED,
        },
        format="json",
    )
    assert response.status_code == 201
    escrow.refresh_from_db()
    assert escrow.status == EscrowStatus.PARTIALLY_FUNDED
    assert escrow.confirmed_funded_amount == Decimal("400000.00")

    response = api_client.post(
        f"/api/v1/payment-escrows/{escrow.id}/record-funding/",
        {
            "provider_event_id": "evt-final",
            "amount": "600000.00",
            "currency": "NGN",
        },
        format="json",
    )
    assert response.status_code == 201
    escrow.refresh_from_db()
    assert escrow.status == EscrowStatus.FUNDED
    assert escrow.funding_status == EscrowFundingStatus.CONFIRMED_BY_PROVIDER


def test_duplicate_provider_funding_event_is_idempotent(escrow, owner):
    first, created = services.record_funding_event(
        escrow=escrow,
        actor=owner,
        provider_event_id="evt-dup",
        amount=Decimal("1000000.00"),
        currency="NGN",
    )
    second, duplicate_created = services.record_funding_event(
        escrow=escrow,
        actor=owner,
        provider_event_id="evt-dup",
        amount=Decimal("1000000.00"),
        currency="NGN",
    )

    assert created is True
    assert duplicate_created is False
    assert second.id == first.id
    assert EscrowFundingEvent.objects.count() == 1


def test_release_requires_provider_confirmed_funding_and_conditions(escrow, owner, buyer):
    services.record_funding_event(
        escrow=escrow,
        actor=owner,
        provider_event_id="evt-funded",
        amount=Decimal("1000000.00"),
        currency="NGN",
    )
    condition = services.create_escrow_condition(
        escrow=escrow,
        actor=owner,
        condition_type=EscrowConditionType.MANUAL_CONDITION,
        description="Buyer handover confirmation.",
    )

    with pytest.raises(ValidationError):
        services.request_release(escrow=escrow, actor=buyer)

    services.satisfy_escrow_condition(condition=condition, actor=owner)
    release = services.request_release(
        escrow=escrow,
        actor=buyer,
        idempotency_key="release-1",
    )

    assert release.status == EscrowReleaseStatus.REQUESTED
    escrow.refresh_from_db()
    assert escrow.status == EscrowStatus.RELEASE_PENDING


def test_release_is_not_confirmed_until_provider_confirmation(escrow, owner, buyer):
    services.record_funding_event(
        escrow=escrow,
        actor=owner,
        provider_event_id="evt-funded",
        amount=Decimal("1000000.00"),
        currency="NGN",
    )
    release = services.request_release(escrow=escrow, actor=buyer)
    approved = services.approve_release(release=release, actor=owner)

    escrow.refresh_from_db()
    assert approved.status == EscrowReleaseStatus.SENT_TO_PROVIDER
    assert escrow.status == EscrowStatus.RELEASE_PENDING

    confirmed = services.confirm_release(
        release=approved,
        actor=owner,
        provider_reference="settlement-123",
    )
    escrow.refresh_from_db()
    assert confirmed.status == EscrowReleaseStatus.CONFIRMED
    assert escrow.status == EscrowStatus.RELEASED


def test_duplicate_release_request_returns_existing_after_status_changes(escrow, owner, buyer):
    services.record_funding_event(
        escrow=escrow,
        actor=owner,
        provider_event_id="evt-funded",
        amount=Decimal("1000000.00"),
        currency="NGN",
    )

    first = services.request_release(escrow=escrow, actor=buyer, idempotency_key="release-dup")
    second = services.request_release(escrow=escrow, actor=buyer, idempotency_key="release-dup")

    assert second.id == first.id


def test_refund_cannot_be_requested_while_release_is_active(escrow, owner, buyer):
    services.record_funding_event(
        escrow=escrow,
        actor=owner,
        provider_event_id="evt-funded",
        amount=Decimal("1000000.00"),
        currency="NGN",
    )
    services.request_release(escrow=escrow, actor=buyer, idempotency_key="release-active")

    with pytest.raises(ValidationError):
        services.request_refund(
            escrow=escrow,
            actor=buyer,
            reason="Conflicting refund.",
            idempotency_key="refund-conflict",
        )


def test_open_dispute_blocks_release(escrow, owner, buyer):
    services.record_funding_event(
        escrow=escrow,
        actor=owner,
        provider_event_id="evt-funded",
        amount=Decimal("1000000.00"),
        currency="NGN",
    )
    services.open_dispute(transaction=escrow.transaction, opened_by=buyer, reason="Not ready.")

    with pytest.raises(ValidationError):
        services.request_release(escrow=escrow, actor=buyer)


def test_refund_is_not_confirmed_until_provider_confirmation(escrow, owner, buyer):
    services.record_funding_event(
        escrow=escrow,
        actor=owner,
        provider_event_id="evt-funded",
        amount=Decimal("1000000.00"),
        currency="NGN",
    )
    refund = services.request_refund(
        escrow=escrow,
        actor=buyer,
        reason="Transaction cancelled.",
    )
    approved = services.approve_refund(refund=refund, actor=owner)

    escrow.refresh_from_db()
    assert approved.status == EscrowRefundStatus.SENT_TO_PROVIDER
    assert escrow.status == EscrowStatus.REFUND_PENDING

    services.confirm_refund(refund=approved, actor=owner, provider_reference="refund-123")
    escrow.refresh_from_db()
    assert escrow.status == EscrowStatus.REFUNDED
    assert escrow.refund_status == EscrowRefundStatus.CONFIRMED


def test_duplicate_refund_request_returns_existing_after_status_changes(escrow, owner, buyer):
    services.record_funding_event(
        escrow=escrow,
        actor=owner,
        provider_event_id="evt-funded",
        amount=Decimal("1000000.00"),
        currency="NGN",
    )

    first = services.request_refund(
        escrow=escrow,
        actor=buyer,
        reason="Transaction cancelled.",
        idempotency_key="refund-dup",
    )
    second = services.request_refund(
        escrow=escrow,
        actor=buyer,
        reason="Transaction cancelled.",
        idempotency_key="refund-dup",
    )

    assert second.id == first.id


def test_release_cannot_be_requested_while_refund_is_active(escrow, owner, buyer):
    services.record_funding_event(
        escrow=escrow,
        actor=owner,
        provider_event_id="evt-funded",
        amount=Decimal("1000000.00"),
        currency="NGN",
    )
    services.request_refund(
        escrow=escrow,
        actor=buyer,
        reason="Transaction cancelled.",
        idempotency_key="refund-active",
    )

    with pytest.raises(ValidationError):
        services.request_release(escrow=escrow, actor=buyer, idempotency_key="release-conflict")


def test_reconciliation_mismatch_does_not_overwrite_escrow_state(escrow, owner):
    services.record_funding_event(
        escrow=escrow,
        actor=owner,
        provider_event_id="evt-funded",
        amount=Decimal("1000000.00"),
        currency="NGN",
    )
    escrow.refresh_from_db()
    before_status = escrow.status

    record = services.reconcile_escrow(
        escrow=escrow,
        actor=owner,
        provider_amount=Decimal("900000.00"),
        provider_status="funded",
        mismatch_details="Provider amount is lower than expected.",
    )

    escrow.refresh_from_db()
    assert record.status == "mismatch"
    assert escrow.reconciliation_status == EscrowReconciliationStatus.MISMATCH
    assert escrow.status == before_status


def test_assigned_manager_requires_manage_transactions_capability(
    api_client,
    escrow,
    other_user,
    owner,
):
    assignment = PropertyAssignment.objects.create(
        property=escrow.transaction.property,
        user=other_user,
        relationship_type=PropertyAssignmentType.AGENT,
        status=PropertyAssignmentStatus.ACTIVE,
        capabilities=[PropertyAssignmentCapability.MANAGE_LISTING],
        assigned_by=owner,
    )
    authenticate(api_client, other_user)

    denied = api_client.post(
        f"/api/v1/payment-escrows/{escrow.id}/record-funding/",
        {
            "provider_event_id": "evt-manager-denied",
            "amount": "1000000.00",
            "currency": "NGN",
        },
        format="json",
    )
    assert denied.status_code == 404

    assignment.capabilities = [PropertyAssignmentCapability.MANAGE_TRANSACTIONS]
    assignment.save(update_fields=["capabilities", "updated_at"])

    allowed = api_client.post(
        f"/api/v1/payment-escrows/{escrow.id}/record-funding/",
        {
            "provider_event_id": "evt-manager-allowed",
            "amount": "1000000.00",
            "currency": "NGN",
        },
        format="json",
    )
    assert allowed.status_code == 201


def test_webhook_signature_rejects_invalid_payload(api_client, escrow_provider):
    response = api_client.post(
        f"/api/v1/escrow-webhooks/{escrow_provider.slug}/",
        {
            "provider_event_id": "evt-bad-sig",
            "event_type": "funding_confirmed",
        },
        HTTP_X_REALITYNG_ESCROW_SIGNATURE="invalid",
        format="json",
    )

    assert response.status_code == 400


def test_webhook_replay_is_idempotent_for_manual_provider(api_client, escrow_provider):
    response = api_client.post(
        f"/api/v1/escrow-webhooks/{escrow_provider.slug}/",
        {
            "provider_event_id": "evt-replay",
            "event_type": "funding_confirmed",
        },
        format="json",
    )
    assert response.status_code == 202

    response = api_client.post(
        f"/api/v1/escrow-webhooks/{escrow_provider.slug}/",
        {
            "provider_event_id": "evt-replay",
            "event_type": "funding_confirmed",
        },
        format="json",
    )
    assert response.status_code == 202


def test_dispute_status_remains_reusable_for_existing_payment_dispute(escrow, buyer):
    dispute = services.open_dispute(
        transaction=escrow.transaction,
        opened_by=buyer,
        reason="Funding disagreement.",
    )

    assert dispute.status == DisputeStatus.OPEN
