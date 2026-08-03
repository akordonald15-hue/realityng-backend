# RealityNG Sprint 9.2 Provider Profiles, Portfolio and Service Areas

## Executive Summary

Sprint 9.2 extends the verified services marketplace foundation with provider-owned profile management, trade selection, service-area management, portfolio image management, and admin moderation. Public service discovery remains backward-compatible: only active approved providers appear publicly, while draft, rejected, suspended, inactive, archived, or pending profiles stay private.

## Backend Scope Delivered

- Provider profile lifecycle: draft, pending review, active, needs more information, rejected, suspended, inactive, archived.
- Owner APIs for creating, editing, submitting, and deactivating the current user's provider profile.
- Trade CRUD with duplicate prevention and one primary trade.
- Service-area CRUD with one primary service area and radius validation.
- Portfolio image model and owner APIs for upload, metadata update, delete, cover selection, and reorder.
- Admin moderation APIs for approve, reject, request more information, suspend, and reactivate.
- Public-safe serializers for provider cards/details, portfolio gallery, service areas, and verification badge snapshots.
- Audit events for profile, trade, service-area, portfolio, and moderation actions.

## Models and Migration

Migration:

```text
apps/services/migrations/0003_portfolioimage_servicearea_is_primary_and_more.py
```

Model changes:

- `ServiceProvider`: moderation timestamps, reviewer, review notes, rejection reason, more-info message, suspension reason.
- `ProviderTrade`: enforces one primary trade per provider.
- `ServiceArea`: adds `is_primary` and primary-area constraint.
- `PortfolioImage`: public media-backed image samples with caption, category, display order, cover flag, and status.

## API Endpoints

Provider owner:

```text
POST   /api/v1/services/provider-profile/
GET    /api/v1/services/provider-profile/me/
PATCH  /api/v1/services/provider-profile/me/
POST   /api/v1/services/provider-profile/submit/
POST   /api/v1/services/provider-profile/deactivate/
```

Trades:

```text
GET    /api/v1/services/provider-profile/trades/
POST   /api/v1/services/provider-profile/trades/
PATCH  /api/v1/services/provider-profile/trades/{id}/
DELETE /api/v1/services/provider-profile/trades/{id}/
```

Service areas:

```text
GET    /api/v1/services/provider-profile/service-areas/
POST   /api/v1/services/provider-profile/service-areas/
PATCH  /api/v1/services/provider-profile/service-areas/{id}/
DELETE /api/v1/services/provider-profile/service-areas/{id}/
```

Portfolio:

```text
GET    /api/v1/services/provider-profile/portfolio/
POST   /api/v1/services/provider-profile/portfolio/
PATCH  /api/v1/services/provider-profile/portfolio/{id}/
DELETE /api/v1/services/provider-profile/portfolio/{id}/
POST   /api/v1/services/provider-profile/portfolio/{id}/cover/
POST   /api/v1/services/provider-profile/portfolio/reorder/
```

Admin moderation:

```text
GET  /api/v1/services/admin/providers/
GET  /api/v1/services/admin/providers/{id}/
POST /api/v1/services/admin/providers/{id}/approve/
POST /api/v1/services/admin/providers/{id}/reject/
POST /api/v1/services/admin/providers/{id}/request-info/
POST /api/v1/services/admin/providers/{id}/suspend/
POST /api/v1/services/admin/providers/{id}/reactivate/
```

## Permissions and Security

- Only authenticated approved artisans, agents, or admins can create provider profiles.
- One provider profile per user in MVP.
- Owners can manage only their own profile, trades, service areas, and portfolio.
- Public APIs return only active approved providers.
- Admin moderation endpoints require admin privileges.
- Providers cannot approve or review their own provider profile.
- Public serializers exclude private address, reviewer notes, rejection reason, suspension reason, and storage object keys.
- Verification documents remain in `apps.trust`; services do not duplicate private verification storage.
- Portfolio uploads use public media storage and validate MIME type, extension, real image content, size, and provider image count.

## Verification Integration

Provider profile approval is separate from trust verification. Public badges are derived from approved, non-expired, non-suspended trust records only. Pending, rejected, expired, or suspended verification states must not be displayed as verified.

## Testing

Focused backend services validation:

```text
24 passed, 17 staticfiles warnings
```

Validation commands run during implementation:

```text
ruff check apps/services config/settings/base.py
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --validate
pytest apps/services/tests
```

OpenAPI validation generated zero errors. Existing enum-name warnings remain non-blocking.

## Known Limitations

- Quote requests, bookings, reviews, complaints, payments, messaging, and notifications are intentionally out of scope.
- Certification-required categories surface the requirement but depend on the existing trust verification workflow.
- Public contact policy may require a later business decision before quote workflows go live.

## Sprint 9.3 Readiness

Sprint 9.3 can build quote/request workflows on top of active approved provider profiles, verified trade categories, service areas, and portfolio galleries without changing the public discovery contract.
