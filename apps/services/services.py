from __future__ import annotations

from decimal import Decimal

from django.db.models import Avg, Count, Q

from apps.accounts.models import User
from apps.accounts.services import create_audit_log
from apps.services.choices import ProviderStatus, ServiceReviewStatus
from apps.services.models import ServiceProvider, ServiceReview


def emit_service_event(
    *,
    actor: User | None,
    action: str,
    entity,
    metadata: dict | None = None,
) -> None:
    create_audit_log(
        actor=actor,
        action=action,
        entity=entity,
        metadata=metadata or {},
    )


def _round_rating(value) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"))


def recalculate_provider_rating(provider: ServiceProvider) -> ServiceProvider:
    published_reviews = ServiceReview.objects.filter(
        provider=provider,
        status=ServiceReviewStatus.PUBLISHED,
    )
    aggregate = published_reviews.aggregate(
        average_rating=Avg("rating"),
        average_quality_rating=Avg("quality_rating"),
        average_punctuality_rating=Avg("punctuality_rating"),
        average_communication_rating=Avg("communication_rating"),
        average_value_rating=Avg("value_rating"),
        published_review_count=Count("id"),
        recommended_count=Count("id", filter=Q(would_recommend=True)),
    )
    review_count = aggregate["published_review_count"] or 0
    recommended_count = aggregate["recommended_count"] or 0
    recommendation_percentage = (
        round((recommended_count / review_count) * 100) if review_count else 0
    )
    completed_jobs_count = provider.service_bookings.filter(status="completed").count()

    provider.average_rating = _round_rating(aggregate["average_rating"])
    provider.average_quality_rating = _round_rating(aggregate["average_quality_rating"])
    provider.average_punctuality_rating = _round_rating(
        aggregate["average_punctuality_rating"]
    )
    provider.average_communication_rating = _round_rating(
        aggregate["average_communication_rating"]
    )
    provider.average_value_rating = _round_rating(aggregate["average_value_rating"])
    provider.published_review_count = review_count
    provider.recommendation_percentage = recommendation_percentage
    provider.completed_jobs_count = completed_jobs_count
    provider.save(
        update_fields=[
            "average_rating",
            "average_quality_rating",
            "average_punctuality_rating",
            "average_communication_rating",
            "average_value_rating",
            "published_review_count",
            "recommendation_percentage",
            "completed_jobs_count",
            "updated_at",
        ]
    )
    emit_service_event(
        actor=None,
        action="service_review.provider_rating_recalculated",
        entity=provider,
        metadata={
            "average_rating": str(provider.average_rating),
            "published_review_count": review_count,
        },
    )
    return provider


def build_review_trust_signals(provider: ServiceProvider) -> list[dict[str, str]]:
    if provider.status != ProviderStatus.ACTIVE:
        return []
    signals: list[dict[str, str]] = []
    if provider.completed_jobs_count:
        signals.append(
            {
                "label": "Completed Jobs",
                "status": "approved",
                "value": str(provider.completed_jobs_count),
            }
        )
    if provider.published_review_count >= 5 and provider.average_rating >= Decimal("4.50"):
        signals.append(
            {
                "label": "Highly Rated",
                "status": "approved",
                "value": str(provider.average_rating),
            }
        )
    if (
        provider.published_review_count >= 5
        and provider.recommendation_percentage >= 80
    ):
        signals.append(
            {
                "label": "Recommended by Customers",
                "status": "approved",
                "value": f"{provider.recommendation_percentage}%",
            }
        )
    return signals
