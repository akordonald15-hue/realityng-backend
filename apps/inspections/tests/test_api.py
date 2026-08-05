from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.accounts.models import AuditLog
from apps.inspections.choices import (
    InspectionReportStatus,
    InspectionRequestStatus,
    WalkthroughStatus,
)
from apps.inspections.models import InspectionAssignment, InspectionReport, PropertyWalkthrough

pytestmark = pytest.mark.django_db


def mp4_file(name="walkthrough.mp4", content_type="video/mp4"):
    return SimpleUploadedFile(name, b"\x00\x00\x00\x18ftypmp42realityng", content_type=content_type)


def image_file(name="evidence.jpg", content_type="image/jpeg"):
    image = Image.new("RGB", (16, 16), color=(24, 92, 63))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


def test_authenticated_user_can_create_inspection_request(api_client, buyer, inspection_payload):
    api_client.force_authenticate(buyer)

    response = api_client.post(
        reverse("inspection-requests-list"), inspection_payload, format="json"
    )

    assert response.status_code == 201
    assert response.data["status"] == InspectionRequestStatus.REQUESTED
    assert AuditLog.objects.filter(action="inspection_request.created").exists()


def test_duplicate_active_inspection_request_is_rejected(api_client, buyer, inspection_payload):
    api_client.force_authenticate(buyer)
    assert (
        api_client.post(
            reverse("inspection-requests-list"), inspection_payload, format="json"
        ).status_code
        == 201
    )

    response = api_client.post(
        reverse("inspection-requests-list"), inspection_payload, format="json"
    )

    assert response.status_code == 400
    assert "active inspection request" in str(response.data).lower()


def test_cross_user_inspection_access_is_denied(api_client, buyer, other_user, inspection_payload):
    api_client.force_authenticate(buyer)
    created = api_client.post(
        reverse("inspection-requests-list"), inspection_payload, format="json"
    )
    api_client.force_authenticate(other_user)

    response = api_client.get(reverse("inspection-requests-detail", args=[created.data["id"]]))

    assert response.status_code == 404


def test_owner_can_upload_walkthrough_but_public_waits_for_approval(
    api_client,
    landlord_owner,
    approved_property,
):
    api_client.force_authenticate(landlord_owner)
    response = api_client.post(
        reverse("inspection-property-walkthrough-create", args=[approved_property.id]),
        {
            "title": "Main apartment walkthrough",
            "description": "Moderated property walkthrough.",
            "video_file": mp4_file(),
        },
        format="multipart",
    )

    assert response.status_code == 201
    walkthrough = PropertyWalkthrough.objects.get(id=response.data["id"])
    assert walkthrough.status == WalkthroughStatus.DRAFT

    public_response = api_client.get(
        reverse("inspection-property-walkthrough-public", args=[approved_property.id])
    )
    assert public_response.status_code == 200
    assert public_response.data == []


def test_non_owner_cannot_upload_walkthrough(api_client, buyer, approved_property):
    api_client.force_authenticate(buyer)

    response = api_client.post(
        reverse("inspection-property-walkthrough-create", args=[approved_property.id]),
        {
            "title": "Unauthorized video",
            "video_file": mp4_file(),
        },
        format="multipart",
    )

    assert response.status_code == 400


def test_admin_approves_walkthrough_for_public_display(
    api_client,
    landlord_owner,
    admin_user,
    approved_property,
):
    api_client.force_authenticate(landlord_owner)
    created = api_client.post(
        reverse("inspection-property-walkthrough-create", args=[approved_property.id]),
        {"title": "Approved video", "video_file": mp4_file()},
        format="multipart",
    )
    walkthrough_id = created.data["id"]
    api_client.post(reverse("inspection-walkthroughs-submit", args=[walkthrough_id]))
    api_client.force_authenticate(admin_user)

    approved = api_client.post(
        reverse("inspection-admin-walkthroughs-approve", args=[walkthrough_id])
    )
    public_response = api_client.get(
        reverse("inspection-property-walkthrough-public", args=[approved_property.id])
    )

    assert approved.status_code == 200
    assert public_response.status_code == 200
    assert public_response.data[0]["id"] == walkthrough_id


def test_admin_assigns_approved_inspector(
    api_client, buyer, admin_user, inspector_user, inspection_payload
):
    api_client.force_authenticate(buyer)
    created = api_client.post(
        reverse("inspection-requests-list"), inspection_payload, format="json"
    )
    api_client.force_authenticate(admin_user)

    response = api_client.post(
        reverse("inspection-admin-requests-assign", args=[created.data["id"]]),
        {"inspector_id": str(inspector_user.id)},
        format="json",
    )

    assert response.status_code == 200
    assert InspectionAssignment.objects.filter(inspector=inspector_user).exists()


def test_inspector_report_evidence_signed_url_is_authorized(
    api_client,
    buyer,
    admin_user,
    inspector_user,
    inspection_payload,
):
    api_client.force_authenticate(buyer)
    created = api_client.post(
        reverse("inspection-requests-list"), inspection_payload, format="json"
    )
    inspection_id = created.data["id"]
    api_client.force_authenticate(admin_user)
    api_client.post(
        reverse("inspection-admin-requests-assign", args=[inspection_id]),
        {"inspector_id": str(inspector_user.id)},
        format="json",
    )
    api_client.force_authenticate(inspector_user)
    report_response = api_client.post(
        reverse("inspection-request-report-create", args=[inspection_id]),
        {"summary": "Structurally fair.", "overall_condition": "fair", "risk_level": "moderate"},
        format="multipart",
    )
    report = InspectionReport.objects.get(id=report_response.data["id"])
    evidence_response = api_client.post(
        reverse("inspection-reports-evidence", args=[report.id]),
        {
            "evidence_type": "photo",
            "file": image_file(),
            "caption": "Front elevation",
            "category": "exterior",
            "visibility": "requester_visible",
        },
        format="multipart",
    )
    evidence_id = evidence_response.data["id"]

    api_client.force_authenticate(buyer)
    signed = api_client.get(reverse("inspection-evidence-signed-url", args=[evidence_id]))

    assert report.status == InspectionReportStatus.DRAFT
    assert evidence_response.status_code == 201
    assert signed.status_code == 200
    assert signed.data["url"]


def test_requester_can_fetch_approved_report_by_inspection_request(
    api_client,
    buyer,
    admin_user,
    inspector_user,
    inspection_payload,
):
    api_client.force_authenticate(buyer)
    created = api_client.post(
        reverse("inspection-requests-list"), inspection_payload, format="json"
    )
    inspection_id = created.data["id"]
    api_client.force_authenticate(admin_user)
    api_client.post(
        reverse("inspection-admin-requests-assign", args=[inspection_id]),
        {"inspector_id": str(inspector_user.id)},
        format="json",
    )
    api_client.force_authenticate(inspector_user)
    report_response = api_client.post(
        reverse("inspection-request-report-create", args=[inspection_id]),
        {"summary": "Structurally fair.", "overall_condition": "fair", "risk_level": "moderate"},
        format="multipart",
    )
    report = InspectionReport.objects.get(id=report_response.data["id"])
    report.approve(reviewer=admin_user)

    api_client.force_authenticate(buyer)
    response = api_client.get(reverse("inspection-request-report-create", args=[inspection_id]))

    assert response.status_code == 200
    assert response.data["id"] == str(report.id)


def test_inspector_can_create_report_with_json_payload(
    api_client,
    buyer,
    admin_user,
    inspector_user,
    inspection_payload,
):
    api_client.force_authenticate(buyer)
    created = api_client.post(
        reverse("inspection-requests-list"), inspection_payload, format="json"
    )
    inspection_id = created.data["id"]
    api_client.force_authenticate(admin_user)
    api_client.post(
        reverse("inspection-admin-requests-assign", args=[inspection_id]),
        {"inspector_id": str(inspector_user.id)},
        format="json",
    )

    api_client.force_authenticate(inspector_user)
    response = api_client.post(
        reverse("inspection-request-report-create", args=[inspection_id]),
        {
            "summary": "The property is suitable for a standard walkthrough.",
            "overall_condition": "good",
            "recommendation": "Proceed with normal due diligence.",
            "risk_level": "low",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["summary"] == "The property is suitable for a standard walkthrough."
