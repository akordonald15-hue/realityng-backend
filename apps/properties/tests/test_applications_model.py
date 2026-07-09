import pytest

from apps.properties.choices import RentalApplicationStatus
from apps.properties.models import RentalApplication


@pytest.fixture
def rental_application(property_listing, other_user):
    return RentalApplication.objects.create(
        property=property_listing,
        applicant=other_user,
        property_owner=property_listing.owner,
        full_name="Ada Okoro",
        email="ada@example.com",
        phone="+2348012345678",
        employment_status="Employed",
        employer_name="RealityNG Demo Holdings",
        monthly_income="850000.00",
        move_in_date="2026-09-01",
        message="I am ready to move in after verification.",
    )


@pytest.mark.django_db
def test_rental_application_status_pipeline(rental_application):
    assert rental_application.status == RentalApplicationStatus.SUBMITTED
    assert rental_application.can_transition_to(RentalApplicationStatus.UNDER_REVIEW)
    assert not rental_application.can_transition_to(RentalApplicationStatus.APPROVED)

    rental_application.transition_to(RentalApplicationStatus.UNDER_REVIEW)
    assert rental_application.status == RentalApplicationStatus.UNDER_REVIEW

    rental_application.transition_to(RentalApplicationStatus.APPROVED)
    assert rental_application.status == RentalApplicationStatus.APPROVED
    assert not rental_application.can_transition_to(RentalApplicationStatus.WITHDRAWN)
