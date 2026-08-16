# RealityNG Sprint 14.2 Security and Integration Review

## Executive Summary

Sprint 14.2 Property Financing Marketplace was reviewed against the current Sprint 14.1 main baseline. The implementation follows the intended product boundary: RealityNG coordinates financing applications, document collection, partner submission, offers, and applicant/admin operations, while financing partners remain responsible for underwriting, credit decisions, rates, contracts, repayments, collections, and regulatory lending obligations.

The review found three release-blocking financing defects and fixed them on the Sprint 14.2 feature branch:

- Financing consent could create duplicate active consent rows and accepted a client-supplied terms version.
- Expired financing offers could still be accepted.
- Financing applications could be created against unapproved property records.

Regression tests were added for these defects and related security surfaces. Financing-specific PostgreSQL validation, the full payments suite, and the full backend PostgreSQL regression now pass on an isolated disposable PostgreSQL 18 cluster. Redis/Celery production-style regression was not completed because Docker and local Redis were unavailable.

## Git Baseline

- Backend branch: `feature/sprint-14.2-property-financing`
- Original reviewed backend head: `e9ce4a2766f20bfe13f2f404f16e100036066978`
- Frontend branch: `feature/sprint-14.2-property-financing`
- Frontend head: `db409f06d3b0878d22f41ead537cd9cba3e0d5e4`
- Merge base: Sprint 14.1 main baseline `2ae338f5b0ea73536002413141b3b541494c53d3`
- No merge, deployment, production migration, release tag, load test, or VPS operation was performed.

## Issues Found and Fixed

### High: Client-controlled and duplicate financing consent

The consent endpoint accepted `accepted_terms_version` from the frontend payload and created a new consent row on repeated consent calls. This could allow a forged terms version and unnecessary duplicate active consent records.

Resolution:

- Removed `accepted_terms_version` from the public consent serializer.
- Forced consent to use `settings.FINANCING_CONSENT_TERMS_VERSION`.
- Made consent grant idempotent using an active consent lookup.
- Added a PostgreSQL-backed partial unique constraint for active consent per application/applicant/terms version.
- Added regression coverage for duplicate consent and client-forged terms versions.

### High: Expired financing offer acceptance

Applicants could accept an active offer after its `expires_at` timestamp had passed.

Resolution:

- Added server-side expiry validation in `accept_financing_offer`.
- Added regression coverage proving expired offers cannot be accepted.
- Expired acceptance now returns a validation error without mutating the offer/application state.

### Medium: Financing applications allowed non-approved properties

The application creation serializer accepted an existing property regardless of marketplace approval status.

Resolution:

- Added `PropertyStatus.APPROVED` validation to financing application creation.
- Added regression coverage for draft/unapproved property rejection.

## Security Review

Validated by added tests:

- Cross-user financing application mutation is denied.
- Cross-user document upload is denied.
- Property owners cannot access applicant private financing documents.
- Invalid financing document content is rejected.
- Applicants cannot mass-assign partner/admin fields.
- Applicants cannot mutate partner offers directly.
- Accepting one offer withdraws other active offers.
- Large Decimal financing amounts remain precise.
- Consent terms version is server-controlled.
- Consent is idempotent.

Reviewed product boundary:

- Frontend copy uses partner-owned language and avoids representing RealityNG as lender, underwriter, credit bureau, loan collector, or repayment processor.
- Partner offers and partner review are treated as external decisions recorded by RealityNG.

## PostgreSQL Validation

Completed successfully on an isolated local PostgreSQL 18 cluster:

- Django database engine confirmed as `django.db.backends.postgresql`.
- Clean migration path passed through payments `0001`, `0002`, `0003`, and `0004`.
- Upgrade path from payments `0001 -> 0002 -> 0003 -> 0004` passed.
- `python manage.py check`: passed.
- `python manage.py makemigrations --check --dry-run`: passed.
- `python manage.py migrate --plan`: passed.
- `python manage.py spectacular --validate`: passed with 0 errors and existing enum warnings only.
- `pytest apps/payments/tests/test_financing_api.py -q`: 17 passed.
- `pytest apps/payments/tests -q --reuse-db`: 64 passed.
- `pytest -q --reuse-db`: 361 passed.

Not completed:

- Redis-backed Celery, Channels, and realtime outbox regression. Docker daemon and local Redis were unavailable.

## Backend Static and Schema Validation

- `ruff check .`: passed after import-order cleanup.
- `python manage.py check`: passed.
- `python manage.py makemigrations --check --dry-run`: passed.
- `python manage.py migrate --plan`: passed.
- `python manage.py spectacular --validate`: passed with 0 errors and existing enum warnings only.

## Frontend Validation

Completed on `feature/sprint-14.2-property-financing`:

- `npm run lint`: passed.
- `npm run typecheck`: passed.
- `npm run test`: 46 test files passed, 91 tests passed.
- `NEXT_PUBLIC_USE_MOCKS=true npm run build`: passed.
- `NEXT_PUBLIC_USE_MOCKS=false NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1 npm run build`: passed.

## Migration Assessment

New backend migration:

- `apps/payments/migrations/0004_financingconsent_unique_active_financing_consent_per_terms.py`

The migration is forward-only and adds a partial unique constraint for active, non-revoked financing consent records. It does not rewrite deployed migrations.

## Remaining Blockers Before Merge Approval

### Blocker: Redis/Celery/Channels regression not completed

Sprint 14.2 did not intentionally modify realtime infrastructure, but the requested regression against Redis-backed Celery/Channels could not be run locally because Docker and Redis were unavailable. This should be completed before production deployment, or explicitly accepted as covered by a separate Sprint 13/14 regression gate.

## Merge Recommendation

NOT READY TO MERGE

The Sprint 14.2 financing defects found during review were fixed and pushed for review, and PostgreSQL regression passed. The Redis/Celery/Channels integration gate still needs a stable isolated Redis environment before merge approval.
