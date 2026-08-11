from decimal import Decimal
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
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
from apps.properties.choices import ListingType, PropertyStatus, PropertyType
from apps.properties.models import Property

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

    assert signed.status_code == 200
    assert signed.data["url"]


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
