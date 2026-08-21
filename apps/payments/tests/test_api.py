from __future__ import annotations

from decimal import Decimal

import pytest

from apps.payments import services
from apps.payments.models import Transaction
from apps.properties.choices import (
    ListingType,
    PropertyAssignmentCapability,
    PropertyAssignmentStatus,
    PropertyAssignmentType,
    PropertyStatus,
    PropertyType,
)
from apps.properties.models import Property, PropertyAssignment

pytestmark = pytest.mark.django_db


def authenticate(api_client, user):
    api_client.force_authenticate(user=user)


def test_buyer_can_create_own_transaction_for_property(api_client, property_listing, buyer):
    authenticate(api_client, buyer)

    response = api_client.post(
        "/api/v1/transactions/",
        {"property_id": str(property_listing.id), "currency": "NGN"},
        format="json",
    )

    assert response.status_code == 201
    transaction = Transaction.objects.get(id=response.data["id"])
    assert transaction.buyer_id == buyer.id
    assert transaction.owner_id == property_listing.owner_id
    assert transaction.property_id == property_listing.id


def test_client_cannot_mass_assign_buyer_or_owner(api_client, property_listing, buyer, other_user):
    authenticate(api_client, buyer)

    response = api_client.post(
        "/api/v1/transactions/",
        {
            "property_id": str(property_listing.id),
            "buyer": str(other_user.id),
            "owner": str(other_user.id),
        },
        format="json",
    )

    assert response.status_code == 201
    transaction = Transaction.objects.get()
    assert transaction.buyer_id == buyer.id
    assert transaction.owner_id == property_listing.owner_id


def test_unrelated_user_cannot_create_transaction_for_application(
    api_client,
    rental_application,
    other_user,
):
    authenticate(api_client, other_user)

    response = api_client.post(
        "/api/v1/transactions/",
        {
            "property_id": str(rental_application.property_id),
            "application_id": str(rental_application.id),
        },
        format="json",
    )

    assert response.status_code == 403


def test_owner_can_create_transaction_for_application(api_client, rental_application, owner):
    authenticate(api_client, owner)

    response = api_client.post(
        "/api/v1/transactions/",
        {
            "property_id": str(rental_application.property_id),
            "application_id": str(rental_application.id),
        },
        format="json",
    )

    assert response.status_code == 201
    transaction = Transaction.objects.get(id=response.data["id"])
    assert transaction.buyer_id == rental_application.applicant_id
    assert transaction.owner_id == owner.id
    assert transaction.application_id == rental_application.id


def test_assigned_manager_can_create_transaction_for_application(
    api_client,
    rental_application,
    other_user,
    owner,
):
    PropertyAssignment.objects.create(
        property=rental_application.property,
        user=other_user,
        relationship_type=PropertyAssignmentType.AGENT,
        status=PropertyAssignmentStatus.ACTIVE,
        capabilities=[PropertyAssignmentCapability.MANAGE_LISTING],
        assigned_by=owner,
    )
    authenticate(api_client, other_user)

    response = api_client.post(
        "/api/v1/transactions/",
        {
            "property_id": str(rental_application.property_id),
            "application_id": str(rental_application.id),
        },
        format="json",
    )

    assert response.status_code == 201


def test_assigned_manager_can_read_and_manage_transaction(
    api_client,
    transaction,
    other_user,
    owner,
):
    PropertyAssignment.objects.create(
        property=transaction.property,
        user=other_user,
        relationship_type=PropertyAssignmentType.AGENT,
        status=PropertyAssignmentStatus.ACTIVE,
        capabilities=[PropertyAssignmentCapability.MANAGE_LISTING],
        assigned_by=owner,
    )
    authenticate(api_client, other_user)

    response = api_client.get(f"/api/v1/transactions/{transaction.id}/")

    assert response.status_code == 200

    response = api_client.post(
        f"/api/v1/transactions/{transaction.id}/milestones/",
        {"title": "Deposit", "amount": "500000.00"},
        format="json",
    )

    assert response.status_code == 201


def test_revoked_assignment_cannot_manage_transaction(
    api_client,
    transaction,
    other_user,
    owner,
):
    PropertyAssignment.objects.create(
        property=transaction.property,
        user=other_user,
        relationship_type=PropertyAssignmentType.AGENT,
        status=PropertyAssignmentStatus.REVOKED,
        capabilities=[PropertyAssignmentCapability.MANAGE_LISTING],
        assigned_by=owner,
    )
    authenticate(api_client, other_user)

    response = api_client.get(f"/api/v1/transactions/{transaction.id}/")

    assert response.status_code == 404


def test_unrelated_user_cannot_read_transaction(api_client, transaction, other_user):
    authenticate(api_client, other_user)

    response = api_client.get(f"/api/v1/transactions/{transaction.id}/")

    assert response.status_code == 404


def test_buyer_cannot_create_milestone(api_client, transaction, buyer):
    authenticate(api_client, buyer)

    response = api_client.post(
        f"/api/v1/transactions/{transaction.id}/milestones/",
        {"title": "Deposit", "amount": "500000.00"},
        format="json",
    )

    assert response.status_code == 403


def test_owner_can_create_milestone(api_client, transaction, owner):
    authenticate(api_client, owner)

    response = api_client.post(
        f"/api/v1/transactions/{transaction.id}/milestones/",
        {"title": "Deposit", "amount": "500000.00"},
        format="json",
    )

    assert response.status_code == 201


def test_only_buyer_can_submit_payment_proof(
    api_client,
    transaction,
    owner,
    valid_proof_file,
):
    milestone = services.create_milestone(
        transaction=transaction,
        actor=owner,
        title="Deposit",
        amount=Decimal("500000.00"),
    )
    authenticate(api_client, owner)

    response = api_client.post(
        f"/api/v1/payment-milestones/{milestone.id}/proofs/",
        {
            "file": valid_proof_file,
            "amount_claimed": "500000.00",
        },
        format="multipart",
    )

    assert response.status_code == 403


def test_payment_proof_serializer_excludes_raw_file_url(
    api_client,
    transaction,
    buyer,
    owner,
    valid_proof_file,
):
    milestone = services.create_milestone(
        transaction=transaction,
        actor=owner,
        title="Deposit",
        amount=Decimal("500000.00"),
    )
    proof = services.submit_payment_proof(
        milestone=milestone,
        uploaded_by=buyer,
        file=valid_proof_file,
        amount_claimed=Decimal("500000.00"),
    )
    authenticate(api_client, buyer)

    response = api_client.get(f"/api/v1/payment-proofs/{proof.id}/")

    assert response.status_code == 200
    assert "file" not in response.data


def test_unrelated_user_cannot_get_payment_proof_signed_url(
    api_client,
    transaction,
    buyer,
    owner,
    other_user,
    valid_proof_file,
):
    milestone = services.create_milestone(
        transaction=transaction,
        actor=owner,
        title="Deposit",
        amount=Decimal("500000.00"),
    )
    proof = services.submit_payment_proof(
        milestone=milestone,
        uploaded_by=buyer,
        file=valid_proof_file,
        amount_claimed=Decimal("500000.00"),
    )
    authenticate(api_client, buyer)
    authorized = api_client.get(f"/api/v1/payment-proofs/{proof.id}/signed-url/")
    authenticate(api_client, other_user)

    response = api_client.get(f"/api/v1/payment-proofs/{proof.id}/signed-url/")

    assert authorized.status_code == 200
    assert authorized.data["url"]
    assert response.status_code == 404


def test_dispute_milestone_must_belong_to_transaction(api_client, transaction, buyer, owner):
    other_property = Property.objects.create(
        owner=owner,
        title="Other approved property",
        description="Another property.",
        property_type=PropertyType.HOUSE,
        listing_type=ListingType.SALE,
        price=Decimal("100000000.00"),
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        address="Other Road",
        status=PropertyStatus.APPROVED,
    )
    other_transaction = Transaction.objects.create(
        property=other_property,
        buyer=buyer,
        owner=owner,
    )
    other_milestone = services.create_milestone(
        transaction=other_transaction,
        actor=owner,
        title="Other deposit",
        amount=Decimal("500000.00"),
    )
    authenticate(api_client, buyer)

    response = api_client.post(
        f"/api/v1/transactions/{transaction.id}/dispute/",
        {"reason": "Wrong milestone.", "milestone": str(other_milestone.id)},
        format="json",
    )

    assert response.status_code == 400
