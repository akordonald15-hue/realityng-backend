from decimal import Decimal
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import AuditLog, User
from apps.construction.choices import (
    ConstructionMilestoneStatus,
    ConstructionProgressUpdateStatus,
    ConstructionProjectStatus,
    ProjectAccessLevel,
    ProjectStakeholderRole,
    ProjectStakeholderStatus,
)
from apps.construction.models import (
    ConstructionMilestone,
    ConstructionProject,
    ProjectStakeholder,
)
from apps.properties.choices import (
    ListingType,
    PropertyAssignmentCapability,
    PropertyAssignmentStatus,
    PropertyAssignmentType,
    PropertyStatus,
    PropertyType,
)
from apps.properties.models import Property, PropertyAssignment
from apps.trust.choices import VerificationStatus, VerificationType
from apps.trust.models import VerificationRequest

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def owner(db):
    return User.objects.create_user(email="construction-owner@example.com", password="Pass12345!")


@pytest.fixture
def investor(db):
    return User.objects.create_user(
        email="diaspora-investor@example.com",
        password="Pass12345!",
    )


@pytest.fixture
def project_manager(db):
    return User.objects.create_user(email="project-manager@example.com", password="Pass12345!")


@pytest.fixture
def stranger(db):
    return User.objects.create_user(email="stranger@example.com", password="Pass12345!")


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        email="construction-admin@example.com",
        password="Pass12345!",
        is_staff=True,
    )


@pytest.fixture
def property_listing(owner):
    return Property.objects.create(
        owner=owner,
        title="Lekki Construction Site",
        description="A property under renovation.",
        property_type=PropertyType.HOUSE,
        listing_type=ListingType.SALE,
        price=Decimal("95000000.00"),
        currency="NGN",
        country="Nigeria",
        state="Lagos",
        city="Lekki",
        address="Freedom Way",
        status=PropertyStatus.APPROVED,
    )


@pytest.fixture
def project(property_listing, owner, project_manager):
    return ConstructionProject.objects.create(
        property=property_listing,
        owner=owner,
        created_by=owner,
        project_manager=project_manager,
        name="Diaspora Duplex Build",
        description="Remote construction monitoring.",
        planned_start_date="2026-08-01",
        planned_end_date="2026-12-20",
    )


def image_file():
    image = Image.new("RGB", (16, 16), color=(24, 92, 63))
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    return SimpleUploadedFile("site.jpg", buffer.getvalue(), content_type="image/jpeg")


def create_property(owner: User, title: str) -> Property:
    return Property.objects.create(
        owner=owner,
        title=title,
        description="A managed property.",
        property_type=PropertyType.HOUSE,
        listing_type=ListingType.SALE,
        price=Decimal("75000000.00"),
        currency="NGN",
        country="Nigeria",
        state="Lagos",
        city="Lekki",
        address="Managed address",
        status=PropertyStatus.APPROVED,
    )


def test_owner_can_create_construction_project(api_client, owner, property_listing):
    api_client.force_authenticate(owner)

    response = api_client.post(
        reverse("construction-projects-list"),
        {
            "property_id": str(property_listing.id),
            "name": "Remote Renovation",
            "description": "Tracked for diaspora oversight.",
            "project_type": "renovation",
            "planned_start_date": "2026-09-01",
            "planned_end_date": "2026-11-30",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["status"] == ConstructionProjectStatus.DRAFT
    assert AuditLog.objects.filter(action="construction_project.created").exists()


def test_stranger_cannot_create_project_for_unowned_property(
    api_client,
    stranger,
    property_listing,
):
    api_client.force_authenticate(stranger)

    response = api_client.post(
        reverse("construction-projects-list"),
        {
            "property_id": str(property_listing.id),
            "name": "Unauthorized Build",
            "project_type": "new_build",
        },
        format="json",
    )

    assert response.status_code == 403


def test_assignment_capability_is_property_scoped(api_client, owner, project_manager):
    property_a = create_property(owner, "Assigned Property A")
    property_b = create_property(owner, "Unassigned Property B")
    PropertyAssignment.objects.create(
        property=property_a,
        user=project_manager,
        relationship_type=PropertyAssignmentType.AGENT,
        status=PropertyAssignmentStatus.ACTIVE,
        capabilities=[PropertyAssignmentCapability.MANAGE_CONSTRUCTION],
        assigned_by=owner,
    )
    api_client.force_authenticate(project_manager)

    allowed = api_client.post(
        reverse("construction-projects-list"),
        {"property_id": str(property_a.id), "name": "Allowed construction"},
        format="json",
    )
    denied = api_client.post(
        reverse("construction-projects-list"),
        {"property_id": str(property_b.id), "name": "Denied construction"},
        format="json",
    )

    assert allowed.status_code == 201
    assert denied.status_code == 403


def test_assignment_capability_does_not_leak_without_required_capability(
    api_client,
    owner,
    project_manager,
    project,
):
    PropertyAssignment.objects.create(
        property=project.property,
        user=project_manager,
        relationship_type=PropertyAssignmentType.AGENT,
        status=PropertyAssignmentStatus.ACTIVE,
        capabilities=[PropertyAssignmentCapability.MANAGE_WALKTHROUGHS],
        assigned_by=owner,
    )
    project.project_manager = None
    project.save(update_fields=["project_manager", "updated_at"])
    api_client.force_authenticate(project_manager)

    detail = api_client.get(reverse("construction-projects-detail", args=[project.slug]))
    listing = api_client.get(reverse("construction-projects-list"))

    assert detail.status_code == 403
    assert all(item["id"] != str(project.id) for item in listing.data["results"])


@pytest.mark.parametrize(
    ("assignment_status", "expires_delta"),
    [
        (PropertyAssignmentStatus.REVOKED, None),
        (PropertyAssignmentStatus.SUSPENDED, None),
        (PropertyAssignmentStatus.ACTIVE, -1),
    ],
)
def test_inactive_or_expired_assignment_cannot_create_project(
    api_client,
    owner,
    property_listing,
    project_manager,
    assignment_status,
    expires_delta,
):
    expires_at = (
        timezone.now() + timezone.timedelta(days=expires_delta)
        if expires_delta is not None
        else None
    )
    PropertyAssignment.objects.create(
        property=property_listing,
        user=project_manager,
        relationship_type=PropertyAssignmentType.AGENT,
        status=assignment_status,
        capabilities=[PropertyAssignmentCapability.MANAGE_CONSTRUCTION],
        assigned_by=owner,
        expires_at=expires_at,
    )
    api_client.force_authenticate(project_manager)

    response = api_client.post(
        reverse("construction-projects-list"),
        {"property_id": str(property_listing.id), "name": "Inactive assignment build"},
        format="json",
    )

    assert response.status_code == 403


def test_property_manager_assignment_requires_approved_trust_verification(
    api_client,
    owner,
    property_listing,
    project_manager,
):
    PropertyAssignment.objects.create(
        property=property_listing,
        user=project_manager,
        relationship_type=PropertyAssignmentType.PROPERTY_MANAGER,
        status=PropertyAssignmentStatus.ACTIVE,
        capabilities=[PropertyAssignmentCapability.MANAGE_CONSTRUCTION],
        assigned_by=owner,
    )
    api_client.force_authenticate(project_manager)

    denied = api_client.post(
        reverse("construction-projects-list"),
        {"property_id": str(property_listing.id), "name": "Unverified manager build"},
        format="json",
    )
    VerificationRequest.objects.create(
        user=project_manager,
        verification_type=VerificationType.AGENT,
        status=VerificationStatus.APPROVED,
    )
    allowed = api_client.post(
        reverse("construction-projects-list"),
        {"property_id": str(property_listing.id), "name": "Verified manager build"},
        format="json",
    )

    assert denied.status_code == 403
    assert allowed.status_code == 201


def test_stakeholder_does_not_gain_property_management_authority(
    api_client,
    project,
    investor,
):
    ProjectStakeholder.objects.create(
        project=project,
        user=investor,
        stakeholder_role=ProjectStakeholderRole.INVESTOR,
        access_level=ProjectAccessLevel.READ_ONLY,
        status=ProjectStakeholderStatus.ACTIVE,
        invited_by=project.owner,
    )
    api_client.force_authenticate(investor)

    response = api_client.post(
        reverse("construction-projects-list"),
        {"property_id": str(project.property_id), "name": "Investor managed build"},
        format="json",
    )

    assert response.status_code == 403


def test_project_stakeholder_can_view_project_but_not_edit(
    api_client,
    project,
    investor,
):
    ProjectStakeholder.objects.create(
        project=project,
        user=investor,
        stakeholder_role=ProjectStakeholderRole.INVESTOR,
        access_level=ProjectAccessLevel.READ_ONLY,
        status=ProjectStakeholderStatus.ACTIVE,
        invited_by=project.owner,
    )
    api_client.force_authenticate(investor)

    detail = api_client.get(reverse("construction-projects-detail", args=[project.slug]))
    update = api_client.patch(
        reverse("construction-projects-detail", args=[project.slug]),
        {"name": "Investor Rename"},
        format="json",
    )

    assert detail.status_code == 200
    assert update.status_code == 403


def test_weighted_progress_update_preserves_history_and_updates_project(
    api_client,
    project,
    project_manager,
):
    milestone = ConstructionMilestone.objects.create(
        project=project,
        name="Foundation",
        sequence=1,
        weight=Decimal("50.00"),
    )
    api_client.force_authenticate(project_manager)
    created = api_client.post(
        reverse("construction-project-updates-list", args=[project.slug]),
        {
            "milestone": str(milestone.id),
            "title": "Foundation poured",
            "summary": "Concrete works completed.",
            "current_progress": "60.00",
        },
        format="json",
    )

    assert created.status_code == 201
    update_id = created.data["id"]
    api_client.post(reverse("construction-project-updates-submit", args=[project.slug, update_id]))
    approved = api_client.post(
        reverse("construction-project-updates-approve", args=[project.slug, update_id])
    )
    project.refresh_from_db()
    milestone.refresh_from_db()

    assert approved.status_code == 200
    assert approved.data["status"] == ConstructionProgressUpdateStatus.APPROVED
    assert milestone.progress_percent == Decimal("60.00")
    assert project.overall_progress == Decimal("60.00")


def test_weighted_progress_calculation_uses_milestone_weights(
    api_client,
    project,
    project_manager,
):
    foundation = ConstructionMilestone.objects.create(
        project=project,
        name="Foundation",
        sequence=1,
        weight=Decimal("30.00"),
        progress_percent=Decimal("100.00"),
    )
    structure = ConstructionMilestone.objects.create(
        project=project,
        name="Structure",
        sequence=2,
        weight=Decimal("40.00"),
        progress_percent=Decimal("50.00"),
    )
    finishing = ConstructionMilestone.objects.create(
        project=project,
        name="Finishing",
        sequence=3,
        weight=Decimal("30.00"),
        progress_percent=Decimal("0.00"),
    )
    api_client.force_authenticate(project_manager)

    for milestone in [foundation, structure, finishing]:
        created = api_client.post(
            reverse("construction-project-updates-list", args=[project.slug]),
            {
                "milestone": str(milestone.id),
                "title": f"{milestone.name} progress",
                "summary": "Progress update.",
                "current_progress": str(milestone.progress_percent),
            },
            format="json",
        )
        api_client.post(
            reverse("construction-project-updates-submit", args=[project.slug, created.data["id"]])
        )
        api_client.post(
            reverse(
                "construction-project-updates-approve",
                args=[project.slug, created.data["id"]],
            )
        )

    project.refresh_from_db()

    assert project.overall_progress == Decimal("50.00")


def test_completed_inspection_required_before_inspection_milestone_completes(
    api_client,
    project,
    project_manager,
):
    milestone = ConstructionMilestone.objects.create(
        project=project,
        name="Foundation",
        sequence=1,
        weight=Decimal("1.00"),
        requires_inspection=True,
    )
    api_client.force_authenticate(project_manager)

    response = api_client.post(
        reverse("construction-project-milestones-progress", args=[project.slug, milestone.id]),
        {"progress_percent": "100.00"},
        format="json",
    )
    milestone.refresh_from_db()

    assert response.status_code == 200
    assert milestone.status == ConstructionMilestoneStatus.AWAITING_INSPECTION


def test_construction_evidence_signed_url_is_authorized(
    api_client,
    project,
    project_manager,
    investor,
    stranger,
):
    ProjectStakeholder.objects.create(
        project=project,
        user=investor,
        stakeholder_role=ProjectStakeholderRole.INVESTOR,
        access_level=ProjectAccessLevel.READ_ONLY,
        status=ProjectStakeholderStatus.ACTIVE,
        invited_by=project.owner,
    )
    api_client.force_authenticate(project_manager)
    created = api_client.post(
        reverse("construction-project-evidence-list", args=[project.slug]),
        {"evidence_type": "photo", "file": image_file(), "caption": "Site progress"},
        format="multipart",
    )
    assert created.status_code == 201

    api_client.force_authenticate(investor)
    signed = api_client.get(
        reverse("construction-project-evidence-signed-url", args=[project.slug, created.data["id"]])
    )

    api_client.force_authenticate(stranger)
    unrelated = api_client.get(
        reverse("construction-project-evidence-signed-url", args=[project.slug, created.data["id"]])
    )

    assert signed.status_code == 200
    assert signed.data["url"]
    assert unrelated.status_code in {403, 404}


def test_milestone_can_request_existing_inspection_flow(
    api_client,
    project,
    project_manager,
):
    milestone = ConstructionMilestone.objects.create(
        project=project,
        name="Structural frame",
        sequence=2,
        weight=Decimal("1.00"),
        requires_inspection=True,
    )
    api_client.force_authenticate(project_manager)

    response = api_client.post(
        reverse(
            "construction-project-milestones-request-inspection",
            args=[project.slug, milestone.id],
        ),
        {
            "purpose": "Confirm structural frame completion",
            "contact_phone": "+2348012345678",
            "contact_email": "pm@example.com",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["inspection_request"]["inspection_type"] == "construction_progress"
