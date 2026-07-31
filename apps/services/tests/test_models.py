import pytest
from django.db import IntegrityError

from apps.services.choices import ProviderStatus, ProviderType
from apps.services.models import ProviderTrade, ServiceProvider, TradeCategory


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
    ProviderTrade.objects.create(
        provider=active_provider,
        category=plumbing_category,
        is_primary=False,
    )

    with pytest.raises(IntegrityError):
        ProviderTrade.objects.create(
            provider=active_provider,
            category=TradeCategory.objects.get(slug="painting"),
            is_primary=True,
        )


@pytest.mark.django_db
def test_seeded_categories_are_database_driven():
    assert TradeCategory.objects.filter(slug="repairs", parent__isnull=True).exists()
    assert TradeCategory.objects.filter(slug="electrical", parent__slug="repairs").exists()
    assert TradeCategory.objects.filter(
        slug="construction",
        parent__slug="construction-services",
    ).exists()
