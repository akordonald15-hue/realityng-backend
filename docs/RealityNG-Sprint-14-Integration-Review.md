# RealityNG Sprint 14 Integration Review

## Scope discovered

Sprint 14 adds payment and transaction proof tracking. It is a recordkeeping workflow only; it does not process money, hold escrow, create payouts, or guarantee funds.

Backend scope:

- `apps.payments`
- `Transaction`
- `PaymentMilestone`
- `PaymentProof`
- `PaymentDispute`
- private payment-proof storage
- payment proof upload validation
- payment lifecycle services
- DRF APIs for transactions, milestones, proofs, and disputes
- admin registration
- OpenAPI integration
- tests

## Stale branch findings

The original backend branch `origin/feature/sprint-14-payments-transactions` was based on Sprint 9.1-era history, with merge base `92e853353e80b273d06c8bd86dc13ac92a8e1616`. Current `origin/main` at review start was `c6af69e724513f0ca4dc9cb2e6dc21ed1c204966`.

The integration was performed on `integration/sprint-14-review` from current `origin/main`.

## Conflicts resolved

- `config/settings/base.py`: preserved Daphne/Channels, notifications, inspections, construction, services, and added payments.
- `config/urls.py`: preserved all Sprint 10-13 routes and added payments routes.
- `docker-compose.yml`: preserved existing private/public bucket policies and added the private payment-proof bucket.
- `apps/payments/migrations/0001_initial.py`: regenerated from current main model state to avoid stale migration assumptions.

## Fixes made during review

- Transaction creation now derives buyer and owner server-side from the authenticated user, property, and optional rental application.
- Application-backed transaction creation is restricted to the property owner, admin, or an explicitly assigned property manager/agent with `manage_listing`.
- Assigned property managers with `manage_listing` can read/manage authorized transactions.
- Revoked/suspended/expired assignments are excluded by the existing property assignment capability service.
- Payment proof serializers no longer expose the raw `file` field or permanent object path.
- Payment proof signed URLs remain behind object-level permissions.
- Transaction, milestone, proof, and dispute models now include integrity indexes and positive amount constraints.
- Payment endpoints now use scoped DRF throttles.
- Added API regression tests for mass assignment, explicit property assignment, IDOR, proof privacy, and dispute milestone validation.

## Security review

Authentication is required for all Sprint 14 APIs.

Authorization is enforced server-side for buyer, owner, admin, and explicit `PropertyAssignmentCapability.MANAGE_LISTING` relationships. Role alone does not grant payment-management authority.

IDOR checks were added for unrelated transaction reads and proof signed URL access.

Sensitive ownership fields are not accepted as authoritative input. They are derived from server-side context.

Private payment proof files use a private S3/MinIO storage backend and signed URL access.

## Migration review

The Sprint 14 migration is a new payments app initial migration depending on current `properties.0010_leadactivity_inquiry_assigned_to_and_more`.

Validated on isolated Docker PostgreSQL 16:

- Django database engine: `django.db.backends.postgresql`
- Host: Docker Compose service `postgres`
- Clean migration: passed
- `migrate --plan`: passed
- `migrate --noinput`: passed

## Validation

Backend validation completed on the integration branch:

- `ruff check .`: passed
- `python manage.py check`: passed
- `python manage.py makemigrations --check --dry-run`: passed
- PostgreSQL migration: passed
- `python manage.py spectacular --validate`: 0 errors, 9 existing enum warnings
- `pytest apps/payments/tests -q`: 29 passed
- `pytest apps/services/tests -q`: 48 passed
- `pytest apps/inspections/tests -q`: 12 passed
- `pytest apps/construction/tests -q`: 15 passed
- `pytest apps/notifications/tests/test_api.py -q`: 22 passed
- `pytest apps/notifications/tests/test_websocket.py -q`: 7 passed
- Targeted properties/lead/security regression: 43 passed
- Full backend suite on PostgreSQL: 326 passed

Notes:

- The Docker pytest runs are slow on the local Windows machine.
- Parallel backend pytest runs must not share the same PostgreSQL test database; one early run failed because two test processes collided while creating/dropping `test_realityng`.

## Follow-ups

- Payment proof notification events can be added in a later communication pass if product wants realtime payment-proof updates.
- User-facing payment copy should continue to avoid escrow, custody, or payment-guarantee language.
- Existing OpenAPI enum naming warnings remain non-blocking and predate Sprint 14.

## Merge recommendation

READY TO MERGE

Sprint 14 is integrated on current main, security-hardening fixes were applied, PostgreSQL validation passed, cross-sprint regressions passed, and no Sprint 15 work was introduced.
