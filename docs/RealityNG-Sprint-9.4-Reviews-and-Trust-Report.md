# RealityNG Sprint 9.4 Reviews, Ratings and Trust Signals

## Executive Summary

Sprint 9.4 adds booking-linked reviews and provider trust signals to the verified services marketplace. Customers can review a provider only after a completed RealityNG service engagement, providers can respond once to their own published reviews, and administrators can moderate reviews through audited actions.

This sprint does not implement payments, complaints resolution, real-time messaging, notification delivery, subscriptions, featured placements, or advanced booking workflows.

## Architecture

The implementation extends `apps.services` and preserves the Sprint 9.1 through Sprint 9.3 foundation:

- `ServiceProvider` remains the public provider profile source of truth.
- `QuoteRequest` remains the lead-generation workflow.
- `ServiceBooking` provides the minimal completed-engagement dependency required for verified reviews.
- `ServiceReview` stores customer reviews linked to completed bookings.
- `ServiceReviewFlag` provides a lightweight abuse-reporting foundation.
- Rating aggregation is handled server-side and uses published booking-linked reviews only.
- Review-derived trust badges remain separate from verification badges from `apps.trust`.

## Models and Migrations

Migrations:

- `apps/services/migrations/0005_servicebooking.py`
- `apps/services/migrations/0006_serviceprovider_average_communication_rating_and_more.py`

Models:

- `ServiceBooking`
- `ServiceReview`
- `ServiceReviewFlag`

Provider aggregate fields:

- `average_rating`
- `average_quality_rating`
- `average_punctuality_rating`
- `average_communication_rating`
- `average_value_rating`
- `published_review_count`
- `completed_jobs_count`
- `recommendation_percentage`

Review statuses:

- `pending`
- `published`
- `flagged`
- `hidden`
- `disputed`
- `removed`

Flag reasons:

- `spam`
- `abusive`
- `false_information`
- `privacy_concern`
- `conflict_of_interest`
- `other`

## API Endpoints

Customer:

- `POST /api/v1/services/reviews/`
- `GET /api/v1/services/reviews/my/`
- `GET /api/v1/services/reviews/{id}/`
- `PATCH /api/v1/services/reviews/{id}/`
- `POST /api/v1/services/reviews/{id}/flag/`

Public:

- `GET /api/v1/services/providers/{provider_slug}/reviews/`

Provider:

- `GET /api/v1/services/provider-profile/reviews/`
- `POST /api/v1/services/reviews/{id}/respond/`

Admin:

- `GET /api/v1/services/admin/reviews/`
- `GET /api/v1/services/admin/reviews/{id}/`
- `POST /api/v1/services/admin/reviews/{id}/publish/`
- `POST /api/v1/services/admin/reviews/{id}/hide/`
- `POST /api/v1/services/admin/reviews/{id}/restore/`
- `POST /api/v1/services/admin/reviews/{id}/remove/`
- `POST /api/v1/services/admin/reviews/{id}/mark-disputed/`

## Rating Calculations

Provider rating summaries are recalculated by `recalculate_provider_rating`.

Rules:

- Only `published` reviews are included.
- Hidden, flagged, disputed, removed, and pending reviews are excluded from public aggregates.
- Dimension averages are calculated independently when dimension ratings exist.
- Recommendation percentage uses published reviews with `would_recommend=true`.
- Completed job count comes from completed service bookings, not from review count.
- Rating fields cannot be directly changed through public API payloads.

## Trust Badge Rules

Verification badges remain sourced from approved trust records.

Review-derived signals are calculated separately:

- `Completed Jobs`: displayed when the provider has completed service engagements.
- `Highly Rated`: requires at least five published reviews and average rating of at least 4.50.
- `Recommended by Customers`: requires at least five published reviews and at least 80 percent recommendations.

These signals do not imply identity, CAC, address, business, or trade verification.

## Moderation Workflow

Admin review actions:

- Publish a pending or restored review.
- Hide a review with a reason.
- Restore a hidden, removed, flagged, or disputed review.
- Remove a review with a reason.
- Mark a review disputed with a reason.

Provider action:

- Respond once to a published review.

Customer action:

- Create one review for an eligible completed booking.
- Edit review content only inside the configured edit window.
- Flag a review through the lightweight reporting endpoint.

## Fraud and Abuse Controls

- One review per completed booking.
- Customer must own the booking.
- Provider cannot review themselves.
- Review cannot be created before service completion.
- Ratings must be integers from 1 to 5.
- Provider response is limited to the reviewed provider.
- Public endpoints expose published reviews only.
- Internal moderation fields, IP address, user agent, and risk metadata remain private.
- Review creation, edits, provider responses, and flags have scoped throttles.

## Audit Events

Events emitted:

- `service_review.created`
- `service_review.updated`
- `service_review.published`
- `service_review.flagged`
- `service_review.hidden`
- `service_review.restored`
- `service_review.removed`
- `service_review.disputed`
- `service_review.provider_responded`
- `service_review.provider_rating_recalculated`

## Security Findings

- Public serializers do not expose customer contact details, internal moderation notes, creation IP, user agent, risk flags, storage keys, or private trust data.
- Provider review queues are scoped to the authenticated provider profile.
- Admin moderation endpoints require admin permissions.
- Hidden, removed, flagged, disputed, and pending reviews are excluded from public provider pages.
- Review-derived badges are based on completed engagement and published review data only.

## Validation Results

- `ruff check apps/services config/settings/base.py`: passed
- `python manage.py check`: passed
- `python manage.py makemigrations --check --dry-run`: passed
- `python manage.py migrate --noinput`: passed
- `python manage.py spectacular --validate`: passed with existing enum-name warnings only
- `pytest apps/services/tests -q`: passed, 39 tests

Full-suite result is recorded in the final Sprint 9.4 closure report after source-control validation.

Known local warning:

- Django staticfiles warning for missing local `staticfiles/` directory. This is unchanged and non-blocking in the local test environment.

## Known Limitations

- The booking lifecycle is intentionally minimal and only supports the completed-engagement dependency needed for reviews.
- No payment, escrow, cancellation penalty, or scheduling workflow.
- No full complaint/dispute workflow beyond review flagging and admin moderation.
- No automated fraud detection service.
- No external moderation provider.
- No AI review generation or review summarization.

## Sprint 9.5 Readiness

Sprint 9.5 can expand operational dashboards and provider/customer service-management workflows using:

- completed engagement records;
- quote request data;
- review summaries;
- public rating aggregates;
- moderation queues;
- audit events.

Future booking, payment, notification, and complaint workflows should extend this foundation rather than replacing it.

