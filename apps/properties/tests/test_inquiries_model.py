import pytest

from apps.properties.choices import InquiryStatus
from apps.properties.models import Inquiry


@pytest.mark.django_db
def test_inquiry_status_pipeline(property_listing, other_user):
    inquiry = Inquiry.objects.create(
        property=property_listing,
        interested_user=other_user,
        property_owner=property_listing.owner,
        inquiry_type="purchase",
        contact_preference="email",
    )

    assert inquiry.can_transition_to(InquiryStatus.CONTACTED)
    assert not inquiry.can_transition_to(InquiryStatus.CONVERTED)

    inquiry.transition_to(InquiryStatus.CONTACTED)
    inquiry.refresh_from_db()

    assert inquiry.status == InquiryStatus.CONTACTED

    with pytest.raises(ValueError):
        inquiry.transition_to(InquiryStatus.CONVERTED)
