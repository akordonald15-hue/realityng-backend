from __future__ import annotations

from decimal import Decimal

import pytest

from apps.payments.choices import FinancingApplicationStatus, FinancingConsentStatus
from apps.payments.models import FinancingApplication, FinancingDocument, FinancingOffer

pytestmark = pytest.mark.django_db


def authenticate(api_client, user):
    api_client.force_authenticate(user=user)


def _application_payload(product, property_listing):
    return {
        "product_id": str(product.id),
        "property_id": str(property_listing.id),
        "requested_amount": "1200000.00",
        "currency": "NGN",
        "purpose": "Finance annual rent for this apartment.",
        "preferred_tenor_months": 6,
        "employment_status": "employed",
        "monthly_income_band": "NGN 1m - 2m",
        "state": "Lagos",
        "city": "Lagos",
        "applicant_message": "I need rent support.",
    }


def _create_application(api_client, buyer, financing_product, property_listing):
    authenticate(api_client, buyer)
    response = api_client.post(
        "/api/v1/financing-applications/",
        _application_payload(financing_product, property_listing),
        format="json",
    )
    assert response.status_code == 201
    return FinancingApplication.objects.get(id=response.data["id"])


def test_public_can_list_active_financing_products(api_client, financing_product):
    response = api_client.get("/api/v1/financing-products/")

    assert response.status_code == 200
    results = response.data["results"] if isinstance(response.data, dict) else response.data
    assert len(results) == 1
    assert results[0]["name"] == financing_product.name
    assert results[0]["partner"]["slug"] == "manual-finance"


def test_applicant_can_create_application_without_mass_assigning_private_fields(
    api_client,
    buyer,
    other_user,
    financing_product,
    property_listing,
):
    authenticate(api_client, buyer)

    payload = _application_payload(financing_product, property_listing)
    payload["applicant"] = str(other_user.id)
    payload["admin_notes"] = "should not be accepted"
    response = api_client.post("/api/v1/financing-applications/", payload, format="json")

    assert response.status_code == 201
    application = FinancingApplication.objects.get(id=response.data["id"])
    assert application.applicant_id == buyer.id
    assert application.admin_notes == ""
    assert "admin_notes" not in response.data


def test_cross_user_cannot_read_financing_application(
    api_client,
    buyer,
    other_user,
    financing_product,
    property_listing,
):
    application = _create_application(api_client, buyer, financing_product, property_listing)
    authenticate(api_client, other_user)

    response = api_client.get(f"/api/v1/financing-applications/{application.id}/")

    assert response.status_code == 404


def test_consent_documents_and_submission_flow(
    api_client,
    buyer,
    financing_product,
    property_listing,
    valid_financing_document_file,
):
    application = _create_application(api_client, buyer, financing_product, property_listing)

    response = api_client.post(
        f"/api/v1/financing-applications/{application.id}/submit/",
        {},
        format="json",
    )
    assert response.status_code == 400

    response = api_client.post(
        f"/api/v1/financing-applications/{application.id}/consent/",
        {"scope": "financing_partner_submission"},
        format="json",
    )
    assert response.status_code == 200
    application.refresh_from_db()
    assert application.consent_status == FinancingConsentStatus.GRANTED

    response = api_client.post(
        f"/api/v1/financing-applications/{application.id}/documents/",
        {"document_type": "identity", "file": valid_financing_document_file},
        format="multipart",
    )
    assert response.status_code == 201

    second_file = valid_financing_document_file.__class__(
        "bank-statement.pdf",
        b"%PDF-1.4\n%second valid financing document",
        content_type="application/pdf",
    )
    response = api_client.post(
        f"/api/v1/financing-applications/{application.id}/documents/",
        {"document_type": "bank_statement", "file": second_file},
        format="multipart",
    )
    assert response.status_code == 201

    response = api_client.post(
        f"/api/v1/financing-applications/{application.id}/submit/",
        {},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["status"] == FinancingApplicationStatus.SUBMITTED


def test_unrelated_user_cannot_access_financing_document_signed_url(
    api_client,
    buyer,
    other_user,
    financing_product,
    property_listing,
    valid_financing_document_file,
):
    application = _create_application(api_client, buyer, financing_product, property_listing)
    document = FinancingDocument.objects.create(
        application=application,
        uploaded_by=buyer,
        document_type="identity",
        file=valid_financing_document_file,
        original_filename="statement.pdf",
        mime_type="application/pdf",
        file_size=valid_financing_document_file.size,
        checksum="a" * 64,
    )
    authenticate(api_client, other_user)

    response = api_client.get(f"/api/v1/financing-documents/{document.id}/signed-url/")

    assert response.status_code == 404


def test_admin_partner_handoff_offer_and_applicant_acceptance(
    api_client,
    buyer,
    admin_user,
    financing_product,
    property_listing,
):
    application = _create_application(api_client, buyer, financing_product, property_listing)
    application.consent_status = FinancingConsentStatus.GRANTED
    application.status = FinancingApplicationStatus.SUBMITTED
    application.submitted_at = application.created_at
    application.save(update_fields=["consent_status", "status", "submitted_at", "updated_at"])

    authenticate(api_client, admin_user)
    response = api_client.post(
        f"/api/v1/admin-financing-applications/{application.id}/submit-to-partner/",
        {"submission_reference": "partner-sub-1", "payload_hash": "b" * 64},
        format="json",
    )
    assert response.status_code == 201
    application.refresh_from_db()
    assert application.status == FinancingApplicationStatus.PARTNER_REVIEW

    response = api_client.post(
        f"/api/v1/admin-financing-applications/{application.id}/record-offer/",
        {
            "offer_reference": "offer-1",
            "approved_amount": "1000000.00",
            "currency": "NGN",
            "tenor_months": 6,
            "interest_rate_display": "Partner-provided rate",
        },
        format="json",
    )
    assert response.status_code == 201
    offer = FinancingOffer.objects.get(id=response.data["id"])

    authenticate(api_client, buyer)
    response = api_client.post(f"/api/v1/financing-offers/{offer.id}/accept/")

    assert response.status_code == 200
    application.refresh_from_db()
    assert application.status == FinancingApplicationStatus.OFFER_ACCEPTED


def test_non_admin_cannot_access_admin_financing_queue(api_client, buyer):
    authenticate(api_client, buyer)

    response = api_client.get("/api/v1/admin-financing-applications/")

    assert response.status_code == 403


def test_product_amount_and_state_limits_are_enforced(
    api_client,
    buyer,
    financing_product,
    property_listing,
):
    authenticate(api_client, buyer)

    payload = _application_payload(financing_product, property_listing)
    payload["requested_amount"] = str(Decimal("99999999.00"))
    response = api_client.post("/api/v1/financing-applications/", payload, format="json")
    assert response.status_code == 400

    payload = _application_payload(financing_product, property_listing)
    payload["state"] = "Kano"
    response = api_client.post("/api/v1/financing-applications/", payload, format="json")
    assert response.status_code == 400
