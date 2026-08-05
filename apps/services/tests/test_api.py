import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status

from apps.accounts.models import AuditLog, UserRole
from apps.services.choices import (
    ProviderStatus,
    ProviderType,
    QuoteRequestStatus,
    ServiceReviewFlagReason,
    ServiceReviewStatus,
)
from apps.services.models import (
    PortfolioImage,
    ProviderTrade,
    QuoteRequest,
    ServiceBooking,
    ServiceProvider,
    ServiceReview,
)


@pytest.mark.django_db
def test_public_can_list_active_categories(api_client):
    response = api_client.get(reverse("service-categories-list"))

    assert response.status_code == status.HTTP_200_OK
    slugs = {category["slug"] for category in response.data}
    assert {"repairs", "utilities", "home-services", "construction-services"}.issubset(slugs)
    repairs = next(category for category in response.data if category["slug"] == "repairs")
    assert any(child["slug"] == "electrical" for child in repairs["children"])


@pytest.mark.django_db
def test_public_provider_list_returns_only_active_providers(
    api_client, active_provider, other_user
):
    ServiceProvider.objects.create(
        user=other_user,
        provider_type=ProviderType.INDIVIDUAL,
        business_name="Draft Cleaner",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        status=ProviderStatus.DRAFT,
    )

    response = api_client.get(reverse("service-providers-list"))

    assert response.status_code == status.HTTP_200_OK
    names = {provider["business_name"] for provider in response.data["results"]}
    assert "Bright Spark Electrical" in names
    assert "Draft Cleaner" not in names


@pytest.mark.django_db
def test_public_provider_list_filters_by_category_and_location(api_client, active_provider):
    response = api_client.get(
        reverse("service-providers-list"),
        {"category": "electrical", "state": "Lagos", "city": "Lagos", "lga": "Eti-Osa"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["slug"] == active_provider.slug


@pytest.mark.django_db
def test_public_provider_search_and_ordering(api_client, active_provider):
    response = api_client.get(
        reverse("service-providers-list"),
        {"search": "inverter", "ordering": "business_name"},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 1
    assert response.data["results"][0]["business_name"] == "Bright Spark Electrical"


@pytest.mark.django_db
def test_public_provider_detail_excludes_moderation_fields(api_client, active_provider):
    response = api_client.get(reverse("service-providers-detail", args=[active_provider.slug]))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["business_name"] == "Bright Spark Electrical"
    assert response.data["portfolio"]["message"]
    assert "private_address" not in response.data
    assert "verification_snapshot" not in response.data


@pytest.mark.django_db
def test_non_admin_cannot_retrieve_unpublished_provider(api_client, user, other_user):
    draft = ServiceProvider.objects.create(
        user=user,
        provider_type=ProviderType.INDIVIDUAL,
        business_name="Hidden Provider",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        status=ProviderStatus.DRAFT,
    )
    api_client.force_authenticate(user=other_user)

    response = api_client.get(reverse("service-providers-detail", args=[draft.slug]))

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_admin_can_retrieve_unpublished_provider(api_client, admin_user, user):
    draft = ServiceProvider.objects.create(
        user=user,
        provider_type=ProviderType.INDIVIDUAL,
        business_name="Admin Visible Provider",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        status=ProviderStatus.DRAFT,
    )
    api_client.force_authenticate(user=admin_user)

    response = api_client.get(reverse("service-providers-detail", args=[draft.slug]))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["business_name"] == "Admin Visible Provider"


@pytest.mark.django_db
def test_approved_artisan_can_create_profile(api_client, approved_artisan_user):
    api_client.force_authenticate(user=approved_artisan_user)

    response = api_client.post(
        reverse("service-provider-profile"),
        {
            "provider_type": ProviderType.INDIVIDUAL,
            "business_name": "Reliable Repairs",
            "headline": "Fast home repairs",
            "biography": "Repairs for diaspora-owned homes.",
            "phone": "+2348011112222",
            "country": "Nigeria",
            "state": "Lagos",
            "city": "Lagos",
            "display_location": "Lagos",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == ProviderStatus.DRAFT
    assert AuditLog.objects.filter(action="service_provider.created").exists()


@pytest.mark.django_db
def test_non_provider_role_cannot_create_profile(api_client, other_user):
    api_client.force_authenticate(user=other_user)

    response = api_client.post(
        reverse("service-provider-profile"),
        {
            "business_name": "Not Allowed",
            "country": "Nigeria",
            "state": "Lagos",
            "city": "Lagos",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_provider_can_manage_trades_and_service_areas(
    api_client,
    active_provider,
    plumbing_category,
):
    active_provider.status = ProviderStatus.DRAFT
    active_provider.save(update_fields=["status", "updated_at"])
    api_client.force_authenticate(user=active_provider.user)

    trade_response = api_client.post(
        reverse("service-provider-profile-trades-list"),
        {
            "category_id": str(plumbing_category.id),
            "years_experience": 4,
            "skill_level": "expert",
            "is_primary": True,
        },
        format="json",
    )
    area_response = api_client.post(
        reverse("service-provider-profile-service-areas-list"),
        {
            "country": "Nigeria",
            "state": "Lagos",
            "city": "Ikeja",
            "service_radius_km": 20,
            "is_primary": True,
        },
        format="json",
    )

    assert trade_response.status_code == status.HTTP_201_CREATED
    assert area_response.status_code == status.HTTP_201_CREATED
    assert active_provider.trades.get(category=plumbing_category).is_primary is True
    assert active_provider.service_areas.get(city="Ikeja").is_primary is True


@pytest.mark.django_db
def test_provider_submission_requires_primary_trade_and_area(api_client, approved_artisan_user):
    provider = ServiceProvider.objects.create(
        user=approved_artisan_user,
        provider_type=ProviderType.INDIVIDUAL,
        business_name="Incomplete Provider",
        headline="Needs setup",
        biography="Almost ready.",
        phone="+2348011112222",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        status=ProviderStatus.DRAFT,
    )
    api_client.force_authenticate(user=approved_artisan_user)

    response = api_client.post(reverse("service-provider-profile-submit"))

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "primary_trade" in response.data["completion"]["missing"]
    assert provider.status == ProviderStatus.DRAFT


@pytest.mark.django_db
def test_complete_provider_can_submit_and_admin_can_approve(
    api_client,
    active_provider,
    admin_user,
):
    active_provider.status = ProviderStatus.DRAFT
    active_provider.save(update_fields=["status", "updated_at"])
    active_provider.service_areas.update(is_primary=True)
    api_client.force_authenticate(user=active_provider.user)

    submit_response = api_client.post(reverse("service-provider-profile-submit"))
    active_provider.refresh_from_db()

    assert submit_response.status_code == status.HTTP_200_OK
    assert active_provider.status == ProviderStatus.PENDING_REVIEW

    api_client.force_authenticate(user=admin_user)
    approve_response = api_client.post(
        reverse("service-admin-providers-approve", args=[active_provider.id]),
        {},
        format="json",
    )
    active_provider.refresh_from_db()

    assert approve_response.status_code == status.HTTP_200_OK
    assert active_provider.status == ProviderStatus.ACTIVE
    assert AuditLog.objects.filter(action="service_provider.approved").exists()


@pytest.mark.django_db
def test_admin_reject_and_request_info_require_messages(api_client, active_provider, admin_user):
    active_provider.status = ProviderStatus.PENDING_REVIEW
    active_provider.save(update_fields=["status", "updated_at"])
    api_client.force_authenticate(user=admin_user)

    reject_response = api_client.post(
        reverse("service-admin-providers-reject", args=[active_provider.id]),
        {},
        format="json",
    )
    info_response = api_client.post(
        reverse("service-admin-providers-request-info", args=[active_provider.id]),
        {},
        format="json",
    )

    assert reject_response.status_code == status.HTTP_400_BAD_REQUEST
    assert info_response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_suspended_provider_is_not_public(api_client, active_provider):
    active_provider.status = ProviderStatus.SUSPENDED
    active_provider.save(update_fields=["status", "updated_at"])

    response = api_client.get(reverse("service-providers-list"))

    names = {provider["business_name"] for provider in response.data["results"]}
    assert active_provider.business_name not in names


@pytest.mark.django_db
def test_portfolio_upload_cover_and_public_gallery(
    api_client,
    active_provider,
    test_image_file,
):
    active_provider.status = ProviderStatus.DRAFT
    active_provider.save(update_fields=["status", "updated_at"])
    api_client.force_authenticate(user=active_provider.user)

    upload_response = api_client.post(
        reverse("service-provider-profile-portfolio-list"),
        {"image": test_image_file("portfolio.jpg"), "caption": "Finished wiring"},
        format="multipart",
    )

    assert upload_response.status_code == status.HTTP_201_CREATED
    assert upload_response.data["is_cover"] is True
    assert PortfolioImage.objects.filter(provider=active_provider).count() == 1
    assert AuditLog.objects.filter(action="service_provider.portfolio_uploaded").exists()

    active_provider.status = ProviderStatus.ACTIVE
    active_provider.save(update_fields=["status", "updated_at"])
    public_response = api_client.get(
        reverse("service-providers-detail", args=[active_provider.slug])
    )

    assert public_response.status_code == status.HTTP_200_OK
    assert public_response.data["portfolio"]["items"][0]["caption"] == "Finished wiring"
    assert "image" not in public_response.data["portfolio"]["items"][0]


@pytest.mark.django_db
def test_portfolio_rejects_invalid_image_content(api_client, active_provider):
    active_provider.status = ProviderStatus.DRAFT
    active_provider.save(update_fields=["status", "updated_at"])
    api_client.force_authenticate(user=active_provider.user)

    response = api_client.post(
        reverse("service-provider-profile-portfolio-list"),
        {"image": SimpleUploadedFile("bad.jpg", b"not an image", content_type="image/jpeg")},
        format="multipart",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_provider_cannot_manage_another_provider_trade(
    api_client,
    active_provider,
    other_user,
    plumbing_category,
):
    other_provider = ServiceProvider.objects.create(
        user=other_user,
        provider_type=ProviderType.INDIVIDUAL,
        business_name="Other Provider",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
    )
    trade = ProviderTrade.objects.create(
        provider=other_provider,
        category=plumbing_category,
    )
    api_client.force_authenticate(user=active_provider.user)

    response = api_client.patch(
        reverse("service-provider-profile-trades-detail", args=[trade.id]),
        {"years_experience": 9},
        format="json",
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_anonymous_user_can_submit_quote_request(api_client, active_provider, electrical_category):
    response = api_client.post(
        reverse(
            "service-provider-quote-request-create",
            kwargs={"provider_slug": active_provider.slug},
        ),
        {
            "service_category_id": str(electrical_category.id),
            "customer_name": "Ada Buyer",
            "project_title": "Fix inverter wiring",
            "project_description": "The inverter trips when the generator comes on.",
            "budget_range": "NGN 100,000 - 250,000",
            "preferred_contact_method": "whatsapp",
            "phone": "+2348090000000",
            "email": "ada@example.com",
            "property_address": "Lekki Phase 1",
            "state": "Lagos",
            "lga": "Eti-Osa",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    quote_request = QuoteRequest.objects.get(project_title="Fix inverter wiring")
    assert quote_request.customer is None
    assert quote_request.provider == active_provider
    assert quote_request.status == QuoteRequestStatus.SUBMITTED
    assert AuditLog.objects.filter(action="service_quote.submitted").exists()


@pytest.mark.django_db
def test_anonymous_quote_request_requires_contact_identity(api_client, active_provider):
    response = api_client.post(
        reverse(
            "service-provider-quote-request-create",
            kwargs={"provider_slug": active_provider.slug},
        ),
        {
            "project_title": "Repair plumbing",
            "project_description": "Leak under the kitchen sink.",
            "preferred_contact_method": "email",
            "state": "Lagos",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "customer_name" in response.data
    assert "phone" in response.data
    assert "email" in response.data


@pytest.mark.django_db
def test_logged_in_quote_request_autofills_customer(api_client, active_provider, other_user):
    other_user.phone_number = "+2348011112222"
    other_user.first_name = "Ada"
    other_user.last_name = "Customer"
    other_user.save(update_fields=["phone_number", "first_name", "last_name", "updated_at"])
    api_client.force_authenticate(user=other_user)

    response = api_client.post(
        reverse(
            "service-provider-quote-request-create",
            kwargs={"provider_slug": active_provider.slug},
        ),
        {
            "project_title": "Install new sockets",
            "project_description": "Need extra wall sockets in two bedrooms.",
            "preferred_contact_method": "phone",
            "state": "Lagos",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    quote_request = QuoteRequest.objects.get(project_title="Install new sockets")
    assert quote_request.customer == other_user
    assert quote_request.customer_name == other_user.full_name
    assert quote_request.phone == other_user.phone_number
    assert quote_request.email == other_user.email


@pytest.mark.django_db
def test_quote_request_rejects_inactive_provider(api_client, user):
    draft_provider = ServiceProvider.objects.create(
        user=user,
        provider_type=ProviderType.INDIVIDUAL,
        business_name="Draft Provider",
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        status=ProviderStatus.DRAFT,
    )

    response = api_client.post(
        reverse(
            "service-provider-quote-request-create",
            kwargs={"provider_slug": draft_provider.slug},
        ),
        {
            "customer_name": "Ada Buyer",
            "project_title": "Paint apartment",
            "project_description": "Need painting estimate.",
            "preferred_contact_method": "email",
            "phone": "+2348090000000",
            "email": "ada@example.com",
            "state": "Lagos",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert QuoteRequest.objects.count() == 0


@pytest.mark.django_db
def test_provider_can_list_and_manage_own_quote_requests(api_client, active_provider):
    quote_request = QuoteRequest.objects.create(
        provider=active_provider,
        service_category=active_provider.trades.get(is_primary=True).category,
        customer_name="Ada Buyer",
        project_title="Service request",
        project_description="Need a quotation.",
        preferred_contact_method="phone",
        phone="+2348090000000",
        email="ada@example.com",
        state="Lagos",
    )
    api_client.force_authenticate(user=active_provider.user)

    list_response = api_client.get(reverse("service-provider-profile-quote-requests-list"))
    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.data["results"][0]["id"] == str(quote_request.id)

    viewed_response = api_client.post(
        reverse("service-provider-profile-quote-requests-mark-viewed", args=[quote_request.id])
    )
    assert viewed_response.status_code == status.HTTP_200_OK
    assert viewed_response.data["status"] == QuoteRequestStatus.VIEWED

    responded_response = api_client.post(
        reverse("service-provider-profile-quote-requests-mark-responded", args=[quote_request.id])
    )
    assert responded_response.status_code == status.HTTP_200_OK
    assert responded_response.data["status"] == QuoteRequestStatus.RESPONDED

    closed_response = api_client.post(
        reverse("service-provider-profile-quote-requests-close-request", args=[quote_request.id])
    )
    assert closed_response.status_code == status.HTTP_200_OK
    assert closed_response.data["status"] == QuoteRequestStatus.CLOSED


@pytest.mark.django_db
def test_provider_cannot_access_another_provider_quote_request(
    api_client,
    active_provider,
    other_user,
    artisan_role,
):
    UserRole.objects.create(user=other_user, role=artisan_role, status="approved")
    other_provider = ServiceProvider.objects.create(
        user=other_user,
        provider_type=ProviderType.INDIVIDUAL,
        business_name="Other Provider",
        country="Nigeria",
        state="Abuja",
        city="Abuja",
        status=ProviderStatus.ACTIVE,
    )
    quote_request = QuoteRequest.objects.create(
        provider=active_provider,
        customer_name="Ada Buyer",
        project_title="Private request",
        project_description="Do not expose this.",
        preferred_contact_method="email",
        phone="+2348090000000",
        email="ada@example.com",
        state="Lagos",
    )
    api_client.force_authenticate(user=other_provider.user)

    response = api_client.get(
        reverse("service-provider-profile-quote-requests-detail", args=[quote_request.id])
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_admin_can_filter_and_close_quote_requests(api_client, admin_user, active_provider):
    quote_request = QuoteRequest.objects.create(
        provider=active_provider,
        customer_name="Ada Buyer",
        project_title="Admin visible request",
        project_description="Needs moderation visibility.",
        preferred_contact_method="email",
        phone="+2348090000000",
        email="ada@example.com",
        state="Lagos",
    )
    api_client.force_authenticate(user=admin_user)

    list_response = api_client.get(
        reverse("service-admin-quote-requests-list"),
        {"status": QuoteRequestStatus.SUBMITTED, "search": "visible"},
    )
    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.data["count"] == 1

    close_response = api_client.post(
        reverse("service-admin-quote-requests-close-request", args=[quote_request.id])
    )
    assert close_response.status_code == status.HTTP_200_OK
    assert close_response.data["status"] == QuoteRequestStatus.CLOSED


def create_completed_service_booking(active_provider, customer):
    booking = ServiceBooking.objects.create(
        customer=customer,
        provider=active_provider,
        service_category=active_provider.trades.get(is_primary=True).category,
        title="Inverter wiring repair",
        service_summary="Provider completed inverter wiring repair.",
    )
    booking.complete()
    booking.refresh_from_db()
    return booking


@pytest.mark.django_db
def test_customer_can_review_only_completed_booking(api_client, active_provider, other_user):
    booking = create_completed_service_booking(active_provider, other_user)
    api_client.force_authenticate(user=other_user)

    response = api_client.post(
        reverse("service-reviews-list"),
        {
            "booking_id": str(booking.id),
            "rating": 5,
            "title": "Excellent electrical work",
            "comment": "The provider arrived prepared and fixed the wiring cleanly.",
            "would_recommend": True,
            "quality_rating": 5,
            "punctuality_rating": 4,
            "communication_rating": 5,
            "value_rating": 5,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    review = ServiceReview.objects.get(booking=booking)
    assert review.customer == other_user
    assert review.provider == active_provider
    assert review.status == ServiceReviewStatus.PENDING
    assert AuditLog.objects.filter(action="service_review.created").exists()


@pytest.mark.django_db
def test_review_rejects_incomplete_booking_and_duplicate(
    api_client,
    active_provider,
    other_user,
):
    incomplete_booking = ServiceBooking.objects.create(
        customer=other_user,
        provider=active_provider,
        title="Pending service",
    )
    completed_booking = create_completed_service_booking(active_provider, other_user)
    ServiceReview.objects.create(
        booking=completed_booking,
        customer=other_user,
        provider=active_provider,
        rating=4,
        title="Already reviewed",
        comment="This booking already has a review.",
    )
    api_client.force_authenticate(user=other_user)

    incomplete_response = api_client.post(
        reverse("service-reviews-list"),
        {
            "booking_id": str(incomplete_booking.id),
            "rating": 5,
            "title": "Too early",
            "comment": "This should not be accepted.",
            "would_recommend": True,
        },
        format="json",
    )
    duplicate_response = api_client.post(
        reverse("service-reviews-list"),
        {
            "booking_id": str(completed_booking.id),
            "rating": 5,
            "title": "Duplicate",
            "comment": "This should not be accepted.",
            "would_recommend": True,
        },
        format="json",
    )

    assert incomplete_response.status_code == status.HTTP_400_BAD_REQUEST
    assert duplicate_response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_review_public_visibility_and_aggregation_after_admin_publish(
    api_client,
    admin_user,
    active_provider,
    other_user,
):
    booking = create_completed_service_booking(active_provider, other_user)
    review = ServiceReview.objects.create(
        booking=booking,
        customer=other_user,
        provider=active_provider,
        rating=5,
        title="Trusted electrician",
        comment="Clear communication and tidy work.",
        would_recommend=True,
        quality_rating=5,
        punctuality_rating=5,
        communication_rating=5,
        value_rating=4,
    )

    public_before = api_client.get(
        reverse("service-provider-reviews", kwargs={"provider_slug": active_provider.slug})
    )
    assert public_before.status_code == status.HTTP_200_OK
    assert public_before.data["count"] == 0

    api_client.force_authenticate(user=admin_user)
    publish_response = api_client.post(reverse("service-admin-reviews-publish", args=[review.id]))
    assert publish_response.status_code == status.HTTP_200_OK

    active_provider.refresh_from_db()
    assert active_provider.published_review_count == 1
    assert str(active_provider.average_rating) == "5.00"

    api_client.force_authenticate(user=None)
    public_after = api_client.get(
        reverse("service-provider-reviews", kwargs={"provider_slug": active_provider.slug})
    )
    assert public_after.status_code == status.HTTP_200_OK
    assert public_after.data["count"] == 1
    assert public_after.data["results"][0]["reviewer_label"].endswith("Verified customer")
    assert "moderation_reason" not in public_after.data["results"][0]


@pytest.mark.django_db
def test_provider_can_respond_once_to_own_published_review(
    api_client,
    admin_user,
    active_provider,
    other_user,
):
    booking = create_completed_service_booking(active_provider, other_user)
    review = ServiceReview.objects.create(
        booking=booking,
        customer=other_user,
        provider=active_provider,
        rating=5,
        title="Helpful provider",
        comment="Helpful and professional.",
    )
    api_client.force_authenticate(user=admin_user)
    api_client.post(reverse("service-admin-reviews-publish", args=[review.id]))
    api_client.force_authenticate(user=active_provider.user)

    response = api_client.post(
        reverse("service-reviews-respond", args=[review.id]),
        {"response": "Thank you for trusting our team."},
        format="json",
    )
    duplicate_response = api_client.post(
        reverse("service-reviews-respond", args=[review.id]),
        {"response": "Second response should fail."},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["provider_response"] == "Thank you for trusting our team."
    assert duplicate_response.status_code == status.HTTP_400_BAD_REQUEST
    assert AuditLog.objects.filter(action="service_review.provider_responded").exists()


@pytest.mark.django_db
def test_admin_can_hide_restore_remove_and_dispute_review(
    api_client,
    admin_user,
    active_provider,
    other_user,
):
    booking = create_completed_service_booking(active_provider, other_user)
    review = ServiceReview.objects.create(
        booking=booking,
        customer=other_user,
        provider=active_provider,
        rating=4,
        title="Review needing moderation",
        comment="Moderation can act on this review.",
    )
    api_client.force_authenticate(user=admin_user)
    api_client.post(reverse("service-admin-reviews-publish", args=[review.id]))

    hide_response = api_client.post(
        reverse("service-admin-reviews-hide", args=[review.id]),
        {"reason": "Contains private information."},
        format="json",
    )
    restore_response = api_client.post(reverse("service-admin-reviews-restore", args=[review.id]))
    disputed_response = api_client.post(
        reverse("service-admin-reviews-mark-disputed", args=[review.id]),
        {"reason": "Provider disputes service details."},
        format="json",
    )
    remove_response = api_client.post(
        reverse("service-admin-reviews-remove", args=[review.id]),
        {"reason": "Confirmed abuse."},
        format="json",
    )

    assert hide_response.data["status"] == ServiceReviewStatus.HIDDEN
    assert restore_response.data["status"] == ServiceReviewStatus.PUBLISHED
    assert disputed_response.data["status"] == ServiceReviewStatus.DISPUTED
    assert remove_response.data["status"] == ServiceReviewStatus.REMOVED
    assert AuditLog.objects.filter(action="service_review.removed").exists()


@pytest.mark.django_db
def test_review_flagging_is_unique_and_hides_from_public_when_high_risk(
    api_client,
    admin_user,
    active_provider,
    other_user,
):
    booking = create_completed_service_booking(active_provider, other_user)
    review = ServiceReview.objects.create(
        booking=booking,
        customer=other_user,
        provider=active_provider,
        rating=5,
        title="Contains private detail",
        comment="This published review will be flagged.",
    )
    api_client.force_authenticate(user=admin_user)
    api_client.post(reverse("service-admin-reviews-publish", args=[review.id]))
    api_client.force_authenticate(user=active_provider.user)

    flag_response = api_client.post(
        reverse("service-reviews-flag", args=[review.id]),
        {
            "reason": ServiceReviewFlagReason.PRIVACY_CONCERN,
            "details": "The review mentions a private access detail.",
        },
        format="json",
    )
    duplicate_flag_response = api_client.post(
        reverse("service-reviews-flag", args=[review.id]),
        {"reason": ServiceReviewFlagReason.SPAM},
        format="json",
    )

    assert flag_response.status_code == status.HTTP_200_OK
    assert flag_response.data["status"] == ServiceReviewStatus.FLAGGED
    assert duplicate_flag_response.status_code == status.HTTP_400_BAD_REQUEST
    assert AuditLog.objects.filter(action="service_review.flagged").exists()

    api_client.force_authenticate(user=None)
    public_response = api_client.get(
        reverse("service-provider-reviews", kwargs={"provider_slug": active_provider.slug})
    )
    assert public_response.data["count"] == 0
