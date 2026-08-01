# RealityNG Sprint 9.3 Quote Requests and Customer Enquiries

## Executive Summary

Sprint 9.3 adds the first lead-generation workflow for the verified services marketplace. Customers can request a quotation from an active approved service provider, while providers can view and manage the resulting quote requests from their dashboard. Admins can monitor and close requests for moderation purposes.

This sprint does not implement bookings, payments, reviews, complaints, messaging, email, SMS, push notifications, or calendar scheduling.

## Architecture

The implementation extends `apps.services` and reuses the Sprint 9.1/9.2 provider foundation:

- `ServiceProvider` remains the provider profile source of truth.
- `TradeCategory` is reused as the requested service category.
- `QuoteRequest` stores the customer enquiry and provider workflow status.
- Audit/event hooks are emitted through the existing audit conventions.
- Public visibility remains restricted to active approved providers.

## Models and Migration

Migration:

- `apps/services/migrations/0004_quoterequest.py`

Model:

- `QuoteRequest`

Key fields:

- customer
- customer_name
- provider
- service_category
- project_title
- project_description
- budget_range
- preferred_contact_method
- phone
- email
- property_address
- state
- lga
- preferred_start_date
- status
- viewed_at
- responded_at
- closed_at
- created_at
- updated_at
- is_deleted

Statuses:

- submitted
- viewed
- responded
- closed
- cancelled

## API List

Public:

- `POST /api/v1/services/providers/{provider_slug}/quote-requests/`

Provider:

- `GET /api/v1/services/provider-profile/quote-requests/`
- `GET /api/v1/services/provider-profile/quote-requests/{id}/`
- `POST /api/v1/services/provider-profile/quote-requests/{id}/mark-viewed/`
- `POST /api/v1/services/provider-profile/quote-requests/{id}/mark-responded/`
- `POST /api/v1/services/provider-profile/quote-requests/{id}/close/`

Admin:

- `GET /api/v1/services/admin/quote-requests/`
- `GET /api/v1/services/admin/quote-requests/{id}/`
- `POST /api/v1/services/admin/quote-requests/{id}/close/`
- `POST /api/v1/services/admin/quote-requests/{id}/cancel/`

Filters:

- status
- search
- ordering=newest|oldest

## Validation Rules

- Anonymous customers must provide name, phone, and email.
- Authenticated users are linked to the quote request and profile contact details are used where available.
- Requests can only target active approved providers.
- Selected service categories must be active and already attached to the provider.
- Phone is required for phone or WhatsApp contact preferences.
- Customers cannot edit quote requests after submission.
- Providers can only access requests sent to their own provider profile.
- Admin endpoints require admin permissions.

## Notification Foundation

Events emitted for future notification delivery:

- `service_quote.submitted`
- `service_quote.viewed`
- `service_quote.responded`
- `service_quote.closed`
- `service_quote.admin_closed`
- `service_quote.admin_cancelled`

No email, SMS, push notification, or messaging delivery was implemented.

## Security Notes

- Draft, pending, rejected, suspended, inactive, archived, and deleted providers cannot receive public quote requests.
- Provider quote queues are owner-scoped.
- Admin quote queues are admin-only.
- Internal provider moderation fields are not part of quote request public responses.
- Rate limiting is configured for public quote request creation and provider/admin management actions.

## Validation Results

- `ruff check .`: passed
- `python manage.py check`: passed
- `python manage.py makemigrations --check --dry-run`: passed
- `python manage.py migrate --noinput`: passed with `services.0004_quoterequest`
- `python manage.py spectacular --validate`: passed, 0 errors, 3 enum-name warnings
- `pytest apps/services/tests`: 31 passed
- `pytest`: 214 passed

Known local warning:

- Django staticfiles warning for missing local `staticfiles/` directory. This is unchanged and non-blocking in the local test environment.

## Jira-Ready Task Breakdown

- Backend: create QuoteRequest model and migration.
- Backend: add public quote request creation endpoint.
- Backend: add provider-owned quote request list/detail/status endpoints.
- Backend: add admin quote request list/detail/moderation endpoints.
- Backend: add serializers, validation, permissions, throttles, admin registration, and audit events.
- Backend: add model/API/permission tests.
- Documentation: update Sprint 9.3 API and validation report.

## Known Limitations

- No booking workflow.
- No payment workflow.
- No messaging or chat.
- No quote response payload or structured price proposal yet.
- No email/SMS/push delivery; only events are emitted.
- No review or complaint workflow.

## Future Work

Recommended next sprint:

- Sprint 9.4: provider quote responses or lightweight booking intake, depending on product priority.

