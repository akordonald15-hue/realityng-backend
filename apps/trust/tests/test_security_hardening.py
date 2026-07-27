"""Security-hardening tests mapped to Sprint 6 Phase 12 requirements.

Covers: self-approval prevention, admin-only endpoint access, cross-user
access denial, and status-transition abuse, mirroring the categories
explicitly called out in the sprint spec.
"""

from __future__ import annotations

import pytest
from rest_framework import status

from apps.trust.services import decide_verification_request
from apps.trust.storage import PrivateVerificationDocumentStorage

pytestmark = pytest.mark.django_db


class TestSelfApprovalPrevention:
    def test_service_layer_blocks_self_review(self, admin_user, verification_request):
        # admin_user reviewing their own submission -- reassign ownership
        # of the request to admin_user to simulate an admin submitting
        # their own verification, then attempting to approve it.
        verification_request.user = admin_user
        verification_request.save(update_fields=["user"])
        with pytest.raises(ValueError, match="cannot review their own"):
            decide_verification_request(
                actor=admin_user,
                verification_request=verification_request,
                status="approved",
            )

    def test_api_blocks_self_approval(self, api_client, admin_user, verification_request):
        verification_request.user = admin_user
        verification_request.save(update_fields=["user"])
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            f"/api/v1/admin/verifications/{verification_request.id}/approve/"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestAdminEndpointAccessControl:
    def test_non_admin_cannot_list_admin_queue(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/v1/admin/verifications/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_non_admin_cannot_approve(self, api_client, user, other_user, verification_request):
        api_client.force_authenticate(user=other_user)
        response = api_client.post(
            f"/api/v1/admin/verifications/{verification_request.id}/approve/"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_access_admin_queue(self, api_client):
        response = api_client.get("/api/v1/admin/verifications/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_admin_can_list_queue(self, api_client, admin_user, verification_request):
        api_client.force_authenticate(user=admin_user)
        response = api_client.get("/api/v1/admin/verifications/")
        assert response.status_code == status.HTTP_200_OK


class TestCrossUserDocumentAccess:
    def test_user_cannot_upload_against_other_users_request(
        self, api_client, other_user, verification_request, valid_pdf_file
    ):
        api_client.force_authenticate(user=other_user)
        response = api_client.post(
            f"/api/v1/verifications/{verification_request.id}/documents/",
            {"document_type": "government_id", "file": valid_pdf_file},
            format="multipart",
        )
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


class TestStatusTransitionAbuse:
    def test_admin_cannot_approve_directly_from_pending(
        self, api_client, admin_user, verification_request
    ):
        # verification_request fixture starts at "pending" -- valid
        # transitions from pending are only under_review or rejected,
        # not approved. This confirms the service layer's transition
        # guard is enforced even for a legitimate (non-self) admin.
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            f"/api/v1/admin/verifications/{verification_request.id}/approve/"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_cannot_reject_an_already_rejected_request(
        self, api_client, admin_user, verification_request
    ):
        verification_request.transition_to("under_review")
        verification_request.transition_to("rejected")
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            f"/api/v1/admin/verifications/{verification_request.id}/reject/"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_valid_admin_review_path_succeeds(self, api_client, admin_user, verification_request):
        verification_request.transition_to("under_review")
        api_client.force_authenticate(user=admin_user)
        response = api_client.post(
            f"/api/v1/admin/verifications/{verification_request.id}/approve/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "approved"


class TestPropertyEditInvalidation:
    def test_material_edit_reverts_approved_verification(
        self, api_client, user, property_listing, property_verification, admin_user
    ):
        property_verification.transition_to("under_review")
        decided_status = "approved"
        property_verification.status = decided_status
        property_verification.reviewer = admin_user
        property_verification.save(update_fields=["status", "reviewer"])

        api_client.force_authenticate(user=user)
        response = api_client.patch(
            f"/api/v1/properties/{property_listing.slug}/",
            {"address": "New Address, Different Street"},
        )
        assert response.status_code == status.HTTP_200_OK

        property_verification.refresh_from_db()
        assert property_verification.status == "under_review"


def test_private_document_storage_uses_configured_signed_url_expiry(settings):
    settings.VERIFICATION_SIGNED_URL_EXPIRY = 17

    storage = PrivateVerificationDocumentStorage()

    assert storage.querystring_expire == 17
