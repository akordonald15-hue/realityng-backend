# RealityNG Version 2.0 Release Summary

## Release Freeze Status

RealityNG Version 2.0 is production deployed and frozen as the Sprint 9.1 through Sprint 9.8 baseline.

No new features were implemented during this freeze. This document records the stable production state that future Sprint 10 work must branch from.

## Production Baseline

Backend runtime deployed to production:

```text
c2b9c62617e9666512a5b5c636715024b217c5ac
```

Backend repository documentation baseline:

```text
9f49e4ee4a9c5015ed8fd56753b41f4acf95cccd
```

Frontend baseline:

```text
6bd152388bd763f97f7e7cafb3a17e48c060e51b
```

Production URLs:

- Backend API: `https://api.realityng.com/api/v1`
- Backend health: `https://api.realityng.com/api/v1/health/`
- Frontend: `https://www.realityng.com`

Shared production dependency:

- Caretekk remains on the same VPS and must not be disrupted by future RealityNG work.

## Tag Status

The `v2.0.0` tag already exists in both repositories.

Backend existing tag target:

```text
a5d8824b8f89f80ca31fad2cc4a4f4b4453952a6
```

Frontend existing tag target:

```text
04c7b68ed085d37e7fab9cd929525b833b6d062f
```

Existing tag message:

```text
RealityNG Version 2.0 — Verification and Guided Assistant Release
```

Release-freeze decision:

- The existing published `v2.0.0` tags were not moved.
- Moving a published release tag would rewrite release history.
- Leadership should approve either preserving the historical `v2.0.0` tag as-is or creating a new immutable release tag for the Sprint 9 production baseline, such as `v2.0.1` or `v2.1.0`.

## Completed Sprint Scope

Completed and production deployed:

- Sprint 0 through Sprint 5: core marketplace foundation
- Sprint 6: verification layer
- Sprint 7: AI assistant framework and demo assistant mode
- Sprint 8: Google Maps and location-intelligence architecture, with production Maps activation deferred
- Sprint 9.1: services marketplace foundation
- Sprint 9.2: provider profiles, portfolio, and service areas
- Sprint 9.3: quote requests and customer enquiries
- Sprint 9.4: booking-linked reviews and trust signals
- Sprint 9.5: operational dashboards
- Sprint 9.6: governance and moderation
- Sprint 9.7: release hardening
- Sprint 9.8: production deployment, smoke testing, and runtime validation

## Production Deployment Summary

Sprint 9.8 deployed the backend safely to the shared VPS.

Deployment characteristics:

- Backend was deployed from an artifact built from local `main`.
- PostgreSQL migrations were applied successfully.
- Only `realityng-backend-1` was recreated.
- RealityNG PostgreSQL, Redis, and MinIO were not recreated.
- Caretekk services were not restarted.
- Nginx routing was not modified.
- No heavy load testing was performed on production.

## Production Health at Freeze

Latest freeze verification:

- RealityNG API health: `200`
- Caretekk health: `200`
- RealityNG backend: healthy
- RealityNG PostgreSQL: healthy
- RealityNG Redis: healthy
- RealityNG MinIO: healthy
- Production rollback point exists
- Sprint 9.8 production deployment report exists

## Validation Metrics

Backend post-merge validation before deployment:

- `ruff check .`: passed
- `python manage.py check`: passed
- `python manage.py makemigrations --check --dry-run`: passed
- `python manage.py migrate --noinput`: passed
- `python manage.py spectacular --validate`: passed with known enum warnings
- `pytest apps/services/tests -q`: 48 passed
- `pytest -q`: 231 passed

Frontend post-merge validation before deployment:

- `npm run lint`: passed
- `npm run typecheck`: passed
- `npm run test`: 36 test files passed, 65 tests passed
- `NEXT_PUBLIC_USE_MOCKS=true npm run build`: passed
- `NEXT_PUBLIC_USE_MOCKS=false NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1 npm run build`: passed

## Freeze Rule

All Sprint 10 work should begin from the latest `origin/main` in both repositories.

Do not branch from old Sprint 9 feature branches.

