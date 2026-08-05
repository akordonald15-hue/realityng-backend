# RealityNG Sprint 10 Release Checklist

## Pre-Release

- Confirm backend and frontend are on the Sprint 10 feature branches.
- Confirm migrations are reviewed.
- Confirm no Caretekk services are touched.
- Confirm walkthrough and inspection storage variables are set.
- Confirm private buckets exist before enabling report/evidence uploads in production.
- Confirm walkthrough bucket/CDN strategy is approved.

## Backend Validation

- `ruff check .`
- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py migrate --noinput`
- `python manage.py spectacular --validate`
- `pytest apps/inspections/tests -q`
- Full backend suite where PostgreSQL/Redis/MinIO are available.

## Frontend Validation

- `npm run lint`
- `npm run typecheck`
- `npm run test`
- `NEXT_PUBLIC_USE_MOCKS=true npm run build`
- `NEXT_PUBLIC_USE_MOCKS=false NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1 npm run build`

## Smoke Tests

- Open property detail.
- Confirm approved walkthroughs render.
- Submit inspection request as a non-owner.
- Confirm owner cannot request inspection for own property.
- Upload walkthrough as eligible property owner.
- Confirm video is not public before approval.
- Approve walkthrough as admin.
- Confirm public property page shows approved walkthrough.
- Assign inspector as admin.
- Create report and evidence as inspector.
- Confirm requester can view approved report and signed evidence.

## Production Safety

- No heavy load testing on the shared VPS.
- No video transcoding jobs on the shared VPS.
- No Caretekk restarts.
- Preserve rollback assets and volumes.
