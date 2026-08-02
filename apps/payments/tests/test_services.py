"""Tests for payments state transitions, validation, and audit logging."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.payments import services
from apps.payments.choices import DisputeStatus, MilestoneStatus, TransactionStatus
from apps.payments.models import Transaction

pytestmark = pytest.mark.django_db


class TestTransactionTransitions:
    def test_create_transaction_starts_as_draft(self, property_listing, buyer, owner):
        txn = services.create_transaction(
            property=property_listing, buyer=buyer, owner=owner, actor=owner,
        )
        assert txn.status == TransactionStatus.DRAFT

    def test_buyer_and_owner_cannot_be_the_same_user(self, property_listing, owner):
        txn = Transaction(property=property_listing, buyer=owner, owner=owner)
        with pytest.raises(ValidationError):
            txn.full_clean()

    def test_activate_from_draft_succeeds(self, transaction, owner):
        services.activate_transaction(transaction, owner)
        transaction.refresh_from_db()
        assert transaction.status == TransactionStatus.ACTIVE

    def test_complete_from_draft_fails(self, transaction, owner):
        with pytest.raises(ValidationError):
            services.complete_transaction(transaction, owner)

    def test_complete_from_active_succeeds(self, transaction, owner):
        services.activate_transaction(transaction, owner)
        services.complete_transaction(transaction, owner)
        transaction.refresh_from_db()
        assert transaction.status == TransactionStatus.COMPLETED

    def test_cannot_transition_out_of_completed(self, transaction, owner):
        services.activate_transaction(transaction, owner)
        services.complete_transaction(transaction, owner)
        with pytest.raises(ValidationError):
            services.cancel_transaction(transaction, owner)


class TestMilestoneAndProofFlow:
    def _milestone(self, transaction, owner):
        return services.create_milestone(
            transaction=transaction, actor=owner, title="Initial deposit",
            amount=Decimal("500000.00"),
        )

    def test_create_milestone_starts_as_pending(self, transaction, owner):
        milestone = self._milestone(transaction, owner)
        assert milestone.status == MilestoneStatus.PENDING

    def test_submit_proof_moves_to_proof_uploaded(self, transaction, buyer, owner, valid_proof_file):
        milestone = self._milestone(transaction, owner)
        proof = services.submit_payment_proof(
            milestone=milestone, uploaded_by=buyer, file=valid_proof_file,
            amount_claimed=Decimal("500000.00"),
        )
        milestone.refresh_from_db()
        assert milestone.status == MilestoneStatus.PROOF_UPLOADED
        assert proof.checksum
        assert proof.original_filename == "receipt.pdf"

    def test_cannot_submit_proof_twice_without_rejection(
        self, transaction, buyer, owner, valid_proof_file
    ):
        milestone = self._milestone(transaction, owner)
        services.submit_payment_proof(
            milestone=milestone, uploaded_by=buyer, file=valid_proof_file,
            amount_claimed=Decimal("500000.00"),
        )
        with pytest.raises(ValidationError):
            services.submit_payment_proof(
                milestone=milestone, uploaded_by=buyer, file=valid_proof_file,
                amount_claimed=Decimal("500000.00"),
            )

    def test_accept_requires_under_review_not_proof_uploaded(
        self, transaction, buyer, owner, valid_proof_file
    ):
        milestone = self._milestone(transaction, owner)
        services.submit_payment_proof(
            milestone=milestone, uploaded_by=buyer, file=valid_proof_file,
            amount_claimed=Decimal("500000.00"),
        )
        with pytest.raises(ValidationError):
            services.accept_milestone(milestone, owner)

    def test_full_review_and_accept_flow(self, transaction, buyer, owner, valid_proof_file):
        milestone = self._milestone(transaction, owner)
        services.submit_payment_proof(
            milestone=milestone, uploaded_by=buyer, file=valid_proof_file,
            amount_claimed=Decimal("500000.00"),
        )
        services.start_milestone_review(milestone, owner)
        services.accept_milestone(milestone, owner, note="Confirmed in bank statement.")
        milestone.refresh_from_db()
        assert milestone.status == MilestoneStatus.ACCEPTED

    def test_reject_then_resubmit_flow(self, transaction, buyer, owner, valid_proof_file):
        milestone = self._milestone(transaction, owner)
        services.submit_payment_proof(
            milestone=milestone, uploaded_by=buyer, file=valid_proof_file,
            amount_claimed=Decimal("500000.00"),
        )
        services.start_milestone_review(milestone, owner)
        services.reject_milestone(milestone, owner, note="Amount doesn't match.")
        milestone.refresh_from_db()
        assert milestone.status == MilestoneStatus.REJECTED

        second_file = valid_proof_file
        second_file.seek(0)
        services.submit_payment_proof(
            milestone=milestone, uploaded_by=buyer, file=second_file,
            amount_claimed=Decimal("500000.00"),
        )
        milestone.refresh_from_db()
        assert milestone.status == MilestoneStatus.PROOF_UPLOADED


class TestDisputes:
    def test_open_dispute_moves_transaction_and_milestone_to_disputed(
        self, transaction, buyer, owner, valid_proof_file
    ):
        services.activate_transaction(transaction, owner)
        milestone = services.create_milestone(
            transaction=transaction, actor=owner, title="Deposit", amount=Decimal("500000.00"),
        )
        services.submit_payment_proof(
            milestone=milestone, uploaded_by=buyer, file=valid_proof_file,
            amount_claimed=Decimal("500000.00"),
        )
        services.start_milestone_review(milestone, owner)
        dispute = services.open_dispute(
            transaction=transaction, opened_by=buyer, reason="Never received confirmation.",
            milestone=milestone,
        )
        transaction.refresh_from_db()
        milestone.refresh_from_db()
        assert transaction.status == TransactionStatus.DISPUTED
        assert milestone.status == MilestoneStatus.DISPUTED
        assert dispute.status == DisputeStatus.OPEN

    def test_resolve_dispute_records_resolver_and_timestamp(self, transaction, buyer, owner):
        services.activate_transaction(transaction, owner)
        dispute = services.open_dispute(
            transaction=transaction, opened_by=buyer, reason="Payment mismatch.",
        )
        resolved = services.resolve_dispute(
            dispute, owner, resolution_note="Confirmed amount was correct.",
        )
        assert resolved.status == DisputeStatus.RESOLVED
        assert resolved.resolved_by_id == owner.id
        assert resolved.resolved_at is not None

    def test_resolve_dispute_rejects_invalid_status(self, transaction, buyer, owner):
        services.activate_transaction(transaction, owner)
        dispute = services.open_dispute(
            transaction=transaction, opened_by=buyer, reason="Payment mismatch.",
        )
        with pytest.raises(ValidationError):
            services.resolve_dispute(dispute, owner, resolution_note="", status="open")
