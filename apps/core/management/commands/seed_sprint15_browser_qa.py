from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.choices import RoleName, UserRoleStatus
from apps.accounts.models import Role, User, UserRole
from apps.inspections.models import (
    InspectionAssignment,
    InspectionEvidence,
    InspectionReport,
    InspectionRequest,
    InspectorProfile,
)
from apps.notifications.models import ConversationParticipant, ConversationThread, Notification
from apps.payments.models import (
    EscrowProvider,
    EscrowTransaction,
    FinancingApplication,
    FinancingDocument,
    FinancingOffer,
    FinancingPartner,
    FinancingProduct,
    PaymentMilestone,
    PaymentProof,
    Transaction,
)
from apps.properties.models import (
    Inquiry,
    Property,
    PropertyAssignment,
    RentalApplication,
    Viewing,
)
from apps.services.models import ServiceProvider, TradeCategory

PASSWORD = "RealityNG-QA-2026!"
PREFIX = "sprint15.qa"


class Command(BaseCommand):
    help = "Create an idempotent, synthetic local dataset for the Sprint 15 browser gate."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")

    @transaction.atomic
    def handle(self, *args, **options):
        users = self._users()
        property_listing = self._property(users)
        provider = self._provider(users["provider"])
        inspections = self._inspections(users, property_listing)
        payment_data = self._payments(users, property_listing)
        thread = self._thread(users, property_listing)

        result = {
            "password": PASSWORD,
            "users": {key: user.email for key, user in users.items()},
            "property": {"id": str(property_listing.id), "slug": property_listing.slug},
            "provider": {"id": str(provider.id), "slug": provider.slug},
            "inspections": {
                key: str(value.id) for key, value in inspections["requests"].items()
            },
            "private_documents": {
                "inspection_report": str(inspections["report"].id),
                "inspection_evidence": str(inspections["evidence"].id),
                "payment_proof": str(payment_data["payment_proof"].id),
                "financing_document": str(payment_data["financing_document"].id),
            },
            "transaction": str(payment_data["transaction"].id),
            "escrow": str(payment_data["escrow"].id),
            "financing": str(payment_data["financing"].id),
            "thread": str(thread.id),
        }
        output = json.dumps(result, sort_keys=True)
        if options["as_json"]:
            self.stdout.write(output)
        else:
            self.stdout.write(self.style.SUCCESS(f"Sprint 15 browser data ready: {output}"))

    def _user(self, name: str, *, is_staff: bool = False) -> User:
        email = f"{PREFIX}.{name}@example.test"
        user, _ = User.objects.update_or_create(
            email=email,
            defaults={
                "first_name": name.replace("_", " ").title(),
                "is_active": True,
                "is_email_verified": True,
                "is_staff": is_staff,
                "is_superuser": is_staff,
                "is_suspended": False,
            },
        )
        user.set_password(PASSWORD)
        user.save(update_fields=["password"])
        return user

    def _role(self, user: User, role_name: str) -> None:
        role, _ = Role.objects.get_or_create(name=role_name)
        UserRole.objects.update_or_create(
            user=user,
            role=role,
            defaults={"status": UserRoleStatus.APPROVED},
        )

    def _users(self) -> dict[str, User]:
        users = {
            "buyer": self._user("buyer"),
            "owner": self._user("owner"),
            "manager": self._user("manager"),
            "revoked_manager": self._user("revoked_manager"),
            "inspector": self._user("inspector"),
            "former_inspector": self._user("former_inspector"),
            "new_inspector": self._user("new_inspector"),
            "provider": self._user("provider"),
            "nonparticipant": self._user("nonparticipant"),
            "admin": self._user("admin", is_staff=True),
        }
        for key, role in {
            "buyer": RoleName.BUYER,
            "owner": RoleName.LANDLORD,
            "manager": RoleName.AGENT,
            "revoked_manager": RoleName.AGENT,
            "inspector": RoleName.INSPECTOR,
            "former_inspector": RoleName.INSPECTOR,
            "new_inspector": RoleName.INSPECTOR,
            "provider": RoleName.ARTISAN,
            "admin": RoleName.ADMIN,
        }.items():
            self._role(users[key], role)
        for key in ("inspector", "former_inspector", "new_inspector"):
            InspectorProfile.objects.update_or_create(
                user=users[key],
                defaults={
                    "display_name": users[key].first_name,
                    "professional_title": "Synthetic QA Inspector",
                    "verification_status": "approved",
                    "active": True,
                },
            )
        return users

    def _property(self, users: dict[str, User]) -> Property:
        listing, _ = Property.objects.update_or_create(
            slug="sprint-15-browser-qa-home",
            defaults={
                "owner": users["owner"],
                "title": "Sprint 15 Synthetic Lekki Home",
                "description": "Synthetic local-only property for real-browser launch QA.",
                "property_type": "house",
                "listing_type": "sale",
                "price": Decimal("125000000.00"),
                "currency": "NGN",
                "country": "Nigeria",
                "state": "Lagos",
                "city": "Lekki",
                "address": "15 Synthetic QA Avenue",
                "display_location": "Lekki, Lagos",
                "bedrooms": 4,
                "bathrooms": 4,
                "parking_spaces": 2,
                "status": "approved",
                "featured": True,
            },
        )
        capabilities = [
            "manage_listing",
            "manage_transactions",
            "manage_leads",
            "manage_walkthroughs",
            "manage_viewings",
            "manage_inspections",
            "manage_construction",
            "view_private_project_data",
        ]
        PropertyAssignment.objects.update_or_create(
            property=listing,
            user=users["manager"],
            defaults={
                "relationship_type": "property_manager",
                "status": "active",
                "capabilities": capabilities,
                "assigned_by": users["owner"],
                "accepted_at": timezone.now(),
                "revoked_at": None,
            },
        )
        PropertyAssignment.objects.update_or_create(
            property=listing,
            user=users["revoked_manager"],
            defaults={
                "relationship_type": "property_manager",
                "status": "revoked",
                "capabilities": capabilities,
                "assigned_by": users["owner"],
                "revoked_at": timezone.now(),
            },
        )
        inquiry, _ = Inquiry.objects.update_or_create(
            property=listing,
            interested_user=users["buyer"],
            defaults={
                "property_owner": users["owner"],
                "inquiry_type": "purchase",
                "message": "Synthetic browser QA inquiry.",
                "contact_preference": "email",
                "status": "contacted",
            },
        )
        viewing, _ = Viewing.objects.update_or_create(
            inquiry=inquiry,
            requester=users["buyer"],
            defaults={
                "property": listing,
                "property_owner": users["owner"],
                "viewing_type": "physical",
                "preferred_date": timezone.localdate() + timedelta(days=7),
                "preferred_time": "10:00",
                "status": "confirmed",
            },
        )
        RentalApplication.objects.update_or_create(
            property=listing,
            applicant=users["buyer"],
            defaults={
                "property_owner": users["owner"],
                "inquiry": inquiry,
                "viewing": viewing,
                "full_name": "Sprint Fifteen Buyer",
                "email": users["buyer"].email,
                "phone": "+2348000000015",
                "employment_status": "employed",
                "monthly_income": Decimal("2500000.00"),
                "move_in_date": timezone.localdate() + timedelta(days=30),
                "status": "approved",
            },
        )
        return listing

    def _provider(self, user: User) -> ServiceProvider:
        category, _ = TradeCategory.objects.update_or_create(
            slug="sprint-15-browser-electrical",
            defaults={"name": "Synthetic Electrical Services", "is_active": True},
        )
        provider, _ = ServiceProvider.objects.update_or_create(
            user=user,
            defaults={
                "provider_type": "individual",
                "business_name": "Sprint 15 Synthetic Services",
                "slug": "sprint-15-synthetic-services",
                "headline": "Local browser QA provider",
                "biography": "Synthetic provider record used only by local browser tests.",
                "email": user.email,
                "state": "Lagos",
                "city": "Lekki",
                "display_location": "Lekki, Lagos",
                "status": "active",
                "published_at": timezone.now(),
            },
        )
        provider.trades.update_or_create(category=category, defaults={"is_primary": True})
        return provider

    def _inspection_request(self, users, listing, key, inspector, assignment_status):
        requester = {
            "active": users["buyer"],
            "declined": users["nonparticipant"],
            "cancelled": users["revoked_manager"],
            "reassigned": users["manager"],
        }[key]
        request, _ = InspectionRequest.objects.update_or_create(
            property=listing,
            requester=requester,
            purpose=f"Sprint 15 {key} authorization check",
            defaults={
                "inspection_type": "general",
                "description": "Synthetic local-only inspection.",
                "contact_phone": "+2348000000015",
                "contact_email": requester.email,
                "status": "assigned",
                "assigned_inspector": inspector,
                "assigned_by": users["admin"],
                "assigned_at": timezone.now(),
            },
        )
        InspectionAssignment.objects.update_or_create(
            inspection_request=request,
            inspector=inspector,
            defaults={
                "assigned_by": users["admin"],
                "status": assignment_status,
                "accepted_at": timezone.now() if assignment_status == "accepted" else None,
                "declined_at": timezone.now() if assignment_status == "declined" else None,
            },
        )
        return request

    def _inspections(self, users, listing):
        active = self._inspection_request(users, listing, "active", users["inspector"], "accepted")
        declined = self._inspection_request(
            users, listing, "declined", users["former_inspector"], "declined"
        )
        cancelled = self._inspection_request(
            users, listing, "cancelled", users["former_inspector"], "cancelled"
        )
        reassigned = self._inspection_request(
            users, listing, "reassigned", users["new_inspector"], "accepted"
        )
        InspectionAssignment.objects.update_or_create(
            inspection_request=reassigned,
            inspector=users["former_inspector"],
            defaults={"assigned_by": users["admin"], "status": "reassigned"},
        )
        report, _ = InspectionReport.objects.update_or_create(
            inspection_request=active,
            defaults={
                "inspector": users["inspector"],
                "summary": "Synthetic inspection report for browser QA.",
                "overall_condition": "good",
                "risk_level": "low",
                "report_document": "inspections/reports/synthetic-report.pdf",
                "report_document_mime_type": "application/pdf",
                "report_document_file_size": 64,
                "status": "submitted",
            },
        )
        evidence, _ = InspectionEvidence.objects.update_or_create(
            inspection_report=report,
            uploaded_by=users["inspector"],
            caption="Synthetic private evidence",
            defaults={
                "evidence_type": "document",
                "file": "inspections/evidence/synthetic-evidence.pdf",
                "mime_type": "application/pdf",
                "file_size": 64,
                "category": "documentation",
                "visibility": "requester_visible",
            },
        )
        return {
            "requests": {
                "active": active,
                "declined": declined,
                "cancelled": cancelled,
                "reassigned": reassigned,
            },
            "report": report,
            "evidence": evidence,
        }

    def _payments(self, users, listing):
        tx, _ = Transaction.objects.update_or_create(
            property=listing,
            buyer=users["buyer"],
            owner=users["owner"],
            defaults={
                "status": "active",
                "currency": "NGN",
                "notes": "Synthetic browser QA transaction.",
            },
        )
        milestone, _ = PaymentMilestone.objects.update_or_create(
            transaction=tx,
            order=1,
            defaults={
                "title": "Synthetic deposit",
                "amount": Decimal("5000000.00"),
                "status": "proof_uploaded",
            },
        )
        payment_proof, _ = PaymentProof.objects.update_or_create(
            milestone=milestone,
            uploaded_by=users["buyer"],
            checksum="0" * 64,
            defaults={
                "file": "payments/proofs/synthetic-proof.pdf",
                "original_filename": "synthetic-proof.pdf",
                "file_size": 64,
                "amount_claimed": Decimal("5000000.00"),
                "reference": "S15-QA-PROOF",
            },
        )
        provider, _ = EscrowProvider.objects.update_or_create(
            slug="sprint-15-manual-escrow",
            defaults={
                "name": "Sprint 15 Manual Escrow Partner",
                "status": "sandbox",
                "integration_mode": "manual",
                "supported_currencies": ["NGN"],
            },
        )
        escrow, _ = EscrowTransaction.objects.update_or_create(
            transaction=tx,
            defaults={
                "provider": provider,
                "currency": "NGN",
                "expected_amount": Decimal("5000000.00"),
                "status": "awaiting_funding",
                "funding_status": "funding_expected",
                "created_by": users["admin"],
            },
        )
        finance_partner, _ = FinancingPartner.objects.update_or_create(
            slug="sprint-15-finance-partner",
            defaults={
                "name": "Sprint 15 Synthetic Finance Partner",
                "status": "active",
                "partner_type": "manual",
                "integration_mode": "manual",
                "supported_products": ["mortgage"],
                "supported_states": ["Lagos"],
                "minimum_amount": Decimal("1000000.00"),
                "maximum_amount": Decimal("100000000.00"),
            },
        )
        product, _ = FinancingProduct.objects.update_or_create(
            partner=finance_partner,
            name="Sprint 15 Mortgage",
            defaults={
                "product_type": "mortgage",
                "status": "active",
                "currency": "NGN",
                "minimum_amount": Decimal("1000000.00"),
                "maximum_amount": Decimal("100000000.00"),
                "minimum_tenor_months": 12,
                "maximum_tenor_months": 240,
            },
        )
        financing, _ = FinancingApplication.objects.update_or_create(
            application_reference="S15-BROWSER-QA",
            defaults={
                "applicant": users["buyer"],
                "property": listing,
                "transaction": tx,
                "product": product,
                "partner": finance_partner,
                "status": "offer_received",
                "requested_amount": Decimal("50000000.00"),
                "currency": "NGN",
                "purpose": "Synthetic property purchase QA",
                "preferred_tenor_months": 120,
                "employment_status": "employed",
                "monthly_income_band": "NGN 2m-5m",
                "state": "Lagos",
                "city": "Lekki",
                "consent_status": "granted",
            },
        )
        financing_document, _ = FinancingDocument.objects.update_or_create(
            application=financing,
            uploaded_by=users["buyer"],
            checksum="1" * 64,
            defaults={
                "document_type": "bank_statement",
                "file": "financing/documents/synthetic-statement.pdf",
                "original_filename": "synthetic-statement.pdf",
                "mime_type": "application/pdf",
                "file_size": 64,
                "status": "uploaded",
            },
        )
        FinancingOffer.objects.update_or_create(
            application=financing,
            offer_reference="S15-QA-OFFER",
            defaults={
                "partner": finance_partner,
                "status": "active",
                "approved_amount": Decimal("45000000.00"),
                "currency": "NGN",
                "tenor_months": 120,
                "interest_rate_display": "Partner-provided illustrative rate",
                "partner_terms_summary": "Decision and terms are owned by the financing partner.",
            },
        )
        return {
            "transaction": tx,
            "escrow": escrow,
            "financing": financing,
            "payment_proof": payment_proof,
            "financing_document": financing_document,
        }

    def _thread(self, users, listing):
        thread, _ = ConversationThread.objects.update_or_create(
            property=listing,
            created_by=users["buyer"],
            defaults={"is_closed": False},
        )
        for user in (users["buyer"], users["owner"]):
            ConversationParticipant.objects.get_or_create(thread=thread, user=user)
        Notification.objects.update_or_create(
            recipient=users["buyer"],
            title="Sprint 15 browser gate ready",
            defaults={
                "notification_type": "system",
                "channel": "in_app",
                "body": "Synthetic local notification for browser QA.",
                "action_url": "/dashboard/messages/",
            },
        )
        return thread
