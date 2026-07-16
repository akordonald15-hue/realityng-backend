"""API-level permission and access control tests."""

from __future__ import annotations

import pytest
from rest_framework import status

from apps.trust.models import VerificationRequest

pytestmark = pytest.mark.django_db


class TestVerificationRequestOwnership:
    def test_user_can_view_own_verification_request(self, api_client, user, verification_request):
        api_client.force_authenticate(user=user)
        response = api_client.get(f"/api/v1/verifications/{verification_request.id}/")
        assert response.status_code == status.HTTP_200_OK

    def test_user_cannot_view_other_users_verification_request(
        self, api_client, other_user, verification_request
    ):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(f"/api/v1/verifications/{verification_request.id}/")
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_user_cannot_access_verifications(self, api_client, verification_request):
        response = api_client.get(f"/api/v1/verifications/{verification_request.id}/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_list_only_shows_own_requests(self, api_client, user, other_user):
        VerificationRequest.objects.create(user=user, verification_type="agent", status="pending")
        VerificationRequest.objects.create(
            user=other_user, verification_type="landlord", status="pending"
        )
        api_client.force_authenticate(user=user)
        response = api_client.get("/api/v1/verifications/")
        assert response.status_code == status.HTTP_200_OK
        returned_user_ids = {str(item["user"]) for item in response.data["results"]}
        assert returned_user_ids == {str(user.id)}


class TestVerificationSubmission:
    def test_user_can_submit_verification_request(self, api_client, user):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            "/api/v1/verifications/",
            {"verification_type": "agent", "business_name": "Test Realty"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "pending"

    def test_duplicate_active_submission_rejected(self, api_client, user, verification_request):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            "/api/v1/verifications/",
            {"verification_type": "agent"},  # same type as verification_request fixture
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestVerificationDocumentUpload:
    def test_owner_can_upload_document(self, api_client, user, verification_request, valid_pdf_file):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            f"/api/v1/verifications/{verification_request.id}/documents/",
            {"document_type": "cac_certificate", "file": valid_pdf_file},
            format="multipart",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_non_owner_cannot_upload_document(
        self, api_client, other_user, verification_request, valid_pdf_file
    ):
        api_client.force_authenticate(user=other_user)
        response = api_client.post(
            f"/api/v1/verifications/{verification_request.id}/documents/",
            {"document_type": "cac_certificate", "file": valid_pdf_file},
            format="multipart",
        )
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_forged_file_upload_rejected(self, api_client, user, verification_request, invalid_pdf_file):
        api_client.force_authenticate(user=user)
        response = api_client.post(
            f"/api/v1/verifications/{verification_request.id}/documents/",
            {"document_type": "cac_certificate", "file": invalid_pdf_file},
            format="multipart",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
