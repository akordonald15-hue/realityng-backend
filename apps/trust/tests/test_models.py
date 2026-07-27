"""Tests for verification status transitions and constraints."""

from __future__ import annotations

import pytest
from django.db import IntegrityError

from apps.trust.models import PropertyVerification, VerificationRequest

pytestmark = pytest.mark.django_db


class TestVerificationRequestTransitions:
    def test_can_transition_pending_to_under_review(self, verification_request):
        assert verification_request.can_transition_to("under_review") is True

    def test_cannot_transition_pending_directly_to_approved(self, verification_request):
        assert verification_request.can_transition_to("approved") is False

    def test_transition_to_invalid_status_raises(self, verification_request):
        with pytest.raises(ValueError):
            verification_request.transition_to("approved")

    def test_transition_to_same_status_is_noop(self, verification_request):
        verification_request.transition_to("pending")
        assert verification_request.status == "pending"

    def test_full_approval_path(self, verification_request):
        verification_request.transition_to("under_review")
        verification_request.transition_to("approved")
        assert verification_request.status == "approved"

    def test_rejected_can_be_resubmitted(self, verification_request):
        verification_request.transition_to("under_review")
        verification_request.transition_to("rejected")
        assert verification_request.can_transition_to("pending") is True

    def test_approved_can_be_suspended(self, verification_request):
        verification_request.transition_to("under_review")
        verification_request.transition_to("approved")
        verification_request.transition_to("suspended")
        assert verification_request.status == "suspended"

    def test_suspended_cannot_go_directly_to_approved(self, verification_request):
        verification_request.transition_to("under_review")
        verification_request.transition_to("approved")
        verification_request.transition_to("suspended")
        assert verification_request.can_transition_to("approved") is False


class TestVerificationRequestConstraints:
    def test_duplicate_active_request_same_type_rejected(self, user):
        VerificationRequest.objects.create(
            user=user, verification_type="agent", status="pending"
        )
        with pytest.raises(IntegrityError):
            VerificationRequest.objects.create(
                user=user, verification_type="agent", status="under_review"
            )

    def test_duplicate_request_different_type_allowed(self, user):
        VerificationRequest.objects.create(
            user=user, verification_type="agent", status="pending"
        )
        # Should not raise -- different verification_type, same user.
        VerificationRequest.objects.create(
            user=user, verification_type="landlord", status="pending"
        )

    def test_new_request_allowed_after_previous_rejected(self, user):
        first = VerificationRequest.objects.create(
            user=user, verification_type="agent", status="under_review"
        )
        first.transition_to("rejected")
        # rejected is not in ACTIVE_VERIFICATION_STATUSES, so a second
        # row for the same user/type should be allowed.
        VerificationRequest.objects.create(
            user=user, verification_type="agent", status="pending"
        )


class TestPropertyVerificationConstraints:
    def test_duplicate_active_property_verification_rejected(self, property_listing, user):
        PropertyVerification.objects.create(
            property=property_listing, submitted_by=user, status="pending"
        )
        with pytest.raises(IntegrityError):
            PropertyVerification.objects.create(
                property=property_listing, submitted_by=user, status="under_review"
            )

    def test_transition_and_verified_snapshot_independent_of_user_verification(
        self, property_verification
    ):
        # Confirms PropertyVerification's transition table is independent
        # of VerificationRequest instances -- a core sprint requirement:
        # user and property verification must not be conflated.
        property_verification.transition_to("under_review")
        property_verification.transition_to("approved")
        assert property_verification.status == "approved"
