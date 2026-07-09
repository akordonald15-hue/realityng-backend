import pytest

from apps.properties.choices import InquiryType, ViewingStatus, ViewingType
from apps.properties.models import Inquiry, Viewing


@pytest.mark.django_db
def test_viewing_status_pipeline(property_listing, other_user):
    inquiry = Inquiry.objects.create(
        property=property_listing,
        interested_user=other_user,
        property_owner=property_listing.owner,
        inquiry_type=InquiryType.PURCHASE,
    )
    viewing = Viewing.objects.create(
        inquiry=inquiry,
        property=property_listing,
        requester=other_user,
        property_owner=property_listing.owner,
        viewing_type=ViewingType.PHYSICAL,
        preferred_date="2026-08-01",
        preferred_time="13:00:00",
    )

    assert viewing.can_transition_to(ViewingStatus.CONFIRMED)
    assert viewing.can_transition_to(ViewingStatus.RESCHEDULED)
    assert not viewing.can_transition_to(ViewingStatus.COMPLETED)

    viewing.transition_to(ViewingStatus.RESCHEDULED)
    viewing.refresh_from_db()

    assert viewing.status == ViewingStatus.RESCHEDULED
    assert viewing.can_transition_to(ViewingStatus.CONFIRMED)

    with pytest.raises(ValueError):
        viewing.transition_to(ViewingStatus.COMPLETED)
