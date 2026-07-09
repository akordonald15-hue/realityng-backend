import pytest
from django.urls import reverse

from apps.accounts.models import AuditLog
from apps.accounts.views import ForgotPasswordView, LoginView, RegisterView, ResetPasswordView
from apps.properties.views import (
    InquiryViewSet,
    PropertyViewSet,
    RentalApplicationViewSet,
    ViewingViewSet,
)


def test_sensitive_endpoints_define_throttle_scopes():
    assert LoginView.throttle_scope == "auth_login"
    assert RegisterView.throttle_scope == "auth_register"
    assert ForgotPasswordView.throttle_scope == "auth_password_reset"
    assert ResetPasswordView.throttle_scope == "auth_password_reset"
    assert PropertyViewSet.throttle_scope_by_action["images"] == "property_upload"
    assert InquiryViewSet.throttle_scope_by_action["create"] == "inquiry_create"
    assert ViewingViewSet.throttle_scope_by_action["create"] == "viewing_create"
    assert RentalApplicationViewSet.throttle_scope_by_action["create"] == "application_create"


@pytest.mark.django_db
def test_dashboard_activity_hides_unrelated_user_events(
    api_client,
    user,
    other_user,
    property_listing,
):
    unrelated_log = AuditLog.objects.create(
        actor=other_user,
        action="application.submitted",
        entity_type="RentalApplication",
        entity_id=property_listing.id,
        metadata={
            "property_id": str(property_listing.id),
            "applicant_id": str(other_user.id),
            "property_owner_id": str(other_user.id),
        },
    )
    visible_log = AuditLog.objects.create(
        actor=user,
        action="property_favorited",
        entity_type="Property",
        entity_id=property_listing.id,
        metadata={"property_id": str(property_listing.id)},
    )
    api_client.force_authenticate(user)

    response = api_client.get(reverse("dashboard-activity"))

    assert response.status_code == 200
    returned_ids = {item["id"] for item in response.data}
    assert str(visible_log.id) in returned_ids
    assert str(unrelated_log.id) not in returned_ids
