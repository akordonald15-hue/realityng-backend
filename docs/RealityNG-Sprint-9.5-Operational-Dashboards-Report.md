# RealityNG Sprint 9.5 Operational Dashboards

## Executive Summary

Sprint 9.5 brings the Sprint 9 services marketplace work into operational dashboards for customers, providers, and administrators. It does not add new marketplace workflows. Instead, it summarizes provider profiles, quotes, completed service engagements, reviews, ratings, moderation queues, category coverage, and recent activity using the existing Sprint 9.1 through Sprint 9.4 models.

## Architecture

The sprint adds read-only dashboard summary endpoints under `apps.services`.

No new database models or migrations were introduced. The endpoints aggregate:

- `ServiceProvider`
- `ProviderTrade`
- `ServiceArea`
- `PortfolioImage`
- `QuoteRequest`
- `ServiceBooking`
- `ServiceReview`
- `ServiceReviewFlag`
- `TradeCategory`

Business rules from previous sprints remain unchanged.

## Dashboard Endpoints

Customer:

- `GET /api/v1/services/dashboard/customer/`

Provider:

- `GET /api/v1/services/dashboard/provider/`

Admin:

- `GET /api/v1/services/dashboard/admin/`

## Customer Summary

The customer dashboard returns:

- summary stats;
- recent quote requests;
- submitted reviews;
- completed bookings eligible for review;
- recently contacted providers;
- recommended providers;
- service categories;
- recent activity timeline.

Visibility rule:

- Customers see only their own quote requests, bookings, and reviews.

## Provider Summary

The provider dashboard returns:

- provider profile summary;
- profile completion;
- quote status counts;
- review status counts;
- latest quote requests;
- latest reviews;
- provider response reminders;
- recent activity timeline.

Visibility rule:

- Providers see only their own provider profile and related service operations.

## Admin Summary

The admin dashboard returns:

- provider approval counts;
- active provider count;
- quote status counts;
- review status counts;
- pending provider queue;
- pending review queue;
- flagged review queue;
- open quote requests;
- service category breakdown;
- geographic coverage breakdown;
- recent moderation activity.

Visibility rule:

- Admin endpoints require admin permissions.

## Performance Notes

- Summary endpoints use existing summarized fields where available.
- Querysets use `select_related()` and `prefetch_related()` through the existing provider, quote, and review queryset helpers.
- Large queues are capped in dashboard responses.
- Status counts are returned as compact dictionaries.
- No expensive per-request review recalculation was introduced.

## Security

- Customer dashboard is authenticated and scoped to the current user.
- Provider dashboard requires an eligible service provider role and scopes data to the current user's provider profile.
- Admin dashboard requires admin permissions.
- Private provider addresses, private verification documents, moderation internals, and fraud metadata remain outside public/customer/provider summaries.

## Validation

Focused validation during implementation:

- `ruff check apps/services --fix`: passed after formatting.
- `pytest apps/services/tests -q`: 42 passed.

Final full validation is recorded in the Sprint 9.5 closure report.

## Jira-Ready Task Breakdown

- Backend: add customer services dashboard summary endpoint.
- Backend: add provider services dashboard summary endpoint.
- Backend: add admin services operations dashboard summary endpoint.
- Backend: add dashboard serializers and activity/stat DTOs.
- Backend: add dashboard ownership and permission tests.
- Backend: document dashboard architecture, performance notes, and security scope.

## Future Improvements

- Add response-time metrics once quote response timestamps are consistently populated.
- Add provider approval-rate trends after more moderation history exists.
- Add scheduled dashboard materialization if service volume grows.
- Add notification delivery in the approved notification sprint.
- Add richer booking workflow only in the approved future booking sprint.

## Scope Confirmation

Sprint 9.5 did not implement bookings, payments, messaging, notifications, scheduling, featured providers, subscriptions, AI recommendations, inspections, construction workflows, or Sprint 9.6 functionality.

