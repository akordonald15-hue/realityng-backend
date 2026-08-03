import pytest
from django.core.exceptions import ValidationError

from apps.services.choices import ProviderStatus, ProviderType, ServiceBookingStatus
from apps.services.models import (
    PortfolioImage,
    ProviderTrade,
    ServiceArea,
    ServiceBooking,
    ServiceProvider,
    TradeCategory,
)


@pytest.mark.django_db
def test_trade_category_slug_is_generated():
    category = TradeCategory.objects.create(name="Generator Maintenance")

    assert category.slug == "generator-maintenance"


@pytest.mark.django_db
def test_service_provider_slug_is_unique(user, other_user):
    first = ServiceProvider.objects.create(
        user=user,
        business_name="Prime Maintenance",
        provider_type=ProviderType.INDIVIDUAL,
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        status=ProviderStatus.ACTIVE,
    )
    second = ServiceProvider.objects.create(
        user=other_user,
        business_name="Prime Maintenance",
        provider_type=ProviderType.INDIVIDUAL,
        country="Nigeria",
        state="Lagos",
        city="Lagos",
        status=ProviderStatus.ACTIVE,
    )

    assert first.slug == "prime-maintenance"
    assert second.slug == "prime-maintenance-2"


@pytest.mark.django_db
def test_provider_can_only_have_one_primary_trade(active_provider, plumbing_category):
    first = active_provider.trades.get(is_primary=True)
    second = ProviderTrade.objects.create(
        provider=active_provider,
        category=plumbing_category,
        is_primary=True,
    )

    first.refresh_from_db()
    assert second.is_primary is True
    assert first.is_primary is False


@pytest.mark.django_db
def test_provider_can_only_have_one_primary_service_area(active_provider):
    first = active_provider.service_areas.get(is_primary=False)
    second = ServiceArea.objects.create(
        provider=active_provider,
        country="Nigeria",
        state="Lagos",
        city="Ikeja",
        is_primary=True,
    )

    first.refresh_from_db()
    assert second.is_primary is True
    assert first.is_primary is False


@pytest.mark.django_db
def test_provider_can_only_have_one_cover_portfolio_image(active_provider, test_image_file):
    first = PortfolioImage.objects.create(
        provider=active_provider,
        image=test_image_file("first.jpg"),
        is_cover=True,
    )
    second = PortfolioImage.objects.create(
        provider=active_provider,
        image=test_image_file("second.jpg"),
        is_cover=True,
    )

    first.refresh_from_db()
    assert second.is_cover is True
    assert first.is_cover is False


@pytest.mark.django_db
def test_seeded_categories_are_database_driven():
    assert TradeCategory.objects.filter(slug="repairs", parent__isnull=True).exists()
    assert TradeCategory.objects.filter(slug="electrical", parent__slug="repairs").exists()
    assert TradeCategory.objects.filter(
        slug="construction",
        parent__slug="construction-services",
    ).exists()


@pytest.mark.django_db
def test_service_booking_completion_controls_review_eligibility(active_provider, other_user):
    booking = ServiceBooking.objects.create(
        customer=other_user,
        provider=active_provider,
        service_category=active_provider.trades.get(is_primary=True).category,
        title="Install inverter wiring",
        service_summary="Completed apartment inverter wiring.",
    )

    assert booking.is_review_eligible is False

    booking.complete()
    booking.refresh_from_db()

    assert booking.status == ServiceBookingStatus.COMPLETED
    assert booking.completed_at is not None
    assert booking.is_review_eligible is True


@pytest.mark.django_db
def test_service_booking_rejects_provider_self_booking(active_provider):
    booking = ServiceBooking(
        customer=active_provider.user,
        provider=active_provider,
        title="Self booking",
    )

    with pytest.raises(ValidationError):
        booking.full_clean()
