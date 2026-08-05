# RealityNG Sprint 9 Release Readiness

## Executive Summary

Sprint 9.1 through Sprint 9.7 is merged to `main` and validated locally after merge. The Services Marketplace is ready for a controlled production deployment window, subject to the operational deployment checklist and production smoke tests.

This release was prepared without deploying automatically and without running heavy load tests on the shared production VPS.

## Repository State

Backend:

- Sprint 9.6 main baseline before Sprint 9.7 merge: `df398a8bc3a1d69316fd073cfa170872824d56f2`
- Sprint 9.7 merged commit: `4ea6d2d05bb46797531d9ac0f8758d362e5408f3`
- Merge method: fast-forward
- Branch pushed: `main`

Frontend:

- Sprint 9.6 main baseline before Sprint 9.7 merge: `f40fdafeff9cfb1cc5d6d3e67fd55eaf680843b0`
- Sprint 9.7 merged commit: `6bd152388bd763f97f7e7cafb3a17e48c060e51b`
- Merge method: fast-forward
- Branch pushed: `main`

## Validation Results

Backend post-merge validation:

- `ruff check .`: passed
- `python manage.py check`: passed
- `python manage.py makemigrations --check --dry-run`: passed
- `python manage.py migrate --noinput`: passed on an isolated clean SQLite validation database
- `python manage.py spectacular --validate`: passed with 6 known enum naming warnings and 0 errors
- `pytest apps/services/tests -q`: 48 passed
- `pytest -q`: 231 passed

Frontend post-merge validation:

- `npm run lint`: passed
- `npm run typecheck`: passed
- `npm run test`: 36 test files passed, 65 tests passed
- `NEXT_PUBLIC_USE_MOCKS=true npm run build`: passed
- `NEXT_PUBLIC_USE_MOCKS=false NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1 npm run build`: passed

Known local validation note:

- Django reports the existing local warning that the `staticfiles` directory does not exist. This warning is unchanged and non-blocking for the release gate.

## Functional Coverage

Validated by automated tests and release-hardening review:

- Authentication and role protection
- Service categories
- Public provider listing
- Provider profile lifecycle
- Trades and service areas
- Portfolio management
- Quote requests
- Minimal service bookings
- Booking-linked reviews
- Rating aggregates
- Review responses and flags
- Customer, provider, and admin dashboards
- Complaints
- Warnings
- Suspensions
- Appeals
- Admin-only moderation
- Maps fallback behavior
- Existing property marketplace regressions

## Security Readiness

Sprint 9.7 hardening covered:

- Suspended providers are hidden publicly
- Suspended providers cannot receive new quote requests
- Suspended providers cannot edit profiles or mutate portfolio assets
- Suspended providers cannot respond to reviews
- Complaint ownership is enforced
- Appeal ownership is enforced
- Admin moderation endpoints remain admin-only
- Complaint evidence upload validation checks MIME type, extension, file size, and file content
- Complaint evidence serializer does not expose permanent public file URLs
- Audit coverage exists for high-risk service marketplace transitions

Remaining security follow-up:

- Run production smoke tests during deployment using synthetic accounts only.
- Confirm production MinIO bucket policies before and after deployment.
- Confirm Cloudflare does not cache private signed evidence or verification content.

## Production Infrastructure Review

RealityNG currently shares infrastructure with Caretekk:

- Hetzner VPS
- Docker
- PostgreSQL
- Redis
- MinIO
- Nginx
- Cloudflare

Known RealityNG services:

- `realityng-backend-1`
- `realityng-postgres-1`
- `realityng-redis-1`
- `realityng-minio-1`

Known shared Nginx container:

- `telehealthapp-nginx-1`

Known public endpoints:

- RealityNG API: `https://api.realityng.com/api/v1`
- RealityNG frontend: `https://www.realityng.com`
- Caretekk API health: `https://api.caretekk.com/health/`

No production infrastructure changes were made during this release gate.

## Production Smoke Test Plan

Run only light smoke tests on production:

- Maximum users: 1 to 2
- Maximum rate: 1 to 2 requests per second
- Duration: 30 to 60 seconds

Smoke test:

- Health endpoint
- Homepage
- Authentication
- Property listing
- Provider listing
- Provider profile
- Quote request
- Customer dashboard
- Provider dashboard
- Admin login
- Complaint submission
- Review submission where eligible test booking exists

Do not run stress, soak, or concurrency testing against the shared VPS.

## Monitoring Checklist

During deployment, monitor:

- CPU
- RAM
- Disk
- Swap
- Docker container restarts
- Backend logs
- PostgreSQL health
- Redis health
- MinIO health
- Nginx health
- Cloudflare status
- RealityNG health endpoint
- Caretekk health endpoint

## Known Risks

- The shared VPS has limited capacity and also hosts Caretekk.
- Production Google Maps activation remains dependent on approved Google Cloud billing and a restricted browser key.
- Load testing must be performed outside production.
- Production smoke tests still need to be run during the actual deployment window.
- Database backup must be verified immediately before deployment.

## Release Recommendation

Sprint 9 is ready for safe deployment planning. Deployment should proceed only during a controlled window with database backup, rollback marker, health checks, and post-deployment smoke testing.

