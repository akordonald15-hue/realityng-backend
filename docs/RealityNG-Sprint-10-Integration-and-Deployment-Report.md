# RealityNG Sprint 10 Integration and Deployment Report

Date: 2026-08-05

## Executive Summary

Sprint 10 was integrated into `main`, validated, and safely deployed to the shared RealityNG VPS. The sprint adds the property inspection and walkthrough layer:

- Inspection request workflow.
- Moderated walkthrough video uploads.
- Inspector profile and assignment foundation.
- Inspection report and private evidence handling.
- Inspection timeline tracking.
- Buyer, inspector, owner, and admin inspection dashboards.
- Frontend inspection routes and property-detail inspection entry points.

Caretekk remained healthy throughout. No Caretekk application code, database, Redis, MinIO, volumes, or Nginx routing blocks were modified.

## Repository State

### Backend

- Repository: `akordonald15-hue/realityng-backend`
- Feature branch: `feature/sprint-10-inspection-workflow`
- Feature commit before integration: `8df5e5bf05ad569521975864153cfedc5751886f`
- Previous `main`: `503e729fdc94c65c0dcc32bb9f6b29dd4d0e922b`
- Final deployed code commit: `4e32b7b83992ef8a4b30991853a9e6f326ade1c9`
- Merge method: fast-forward, followed by two release fixes on `main`
- Push status: pushed to `origin/main`

Release fixes applied after the feature merge:

- `17c7248f7319279e2b1c658b6d9f187ccb3f7ce7` - added inspection/walkthrough bucket initialization to Docker Compose.
- `4e32b7b83992ef8a4b30991853a9e6f326ade1c9` - allowed JSON payloads for request-scoped inspection report creation.

### Frontend

- Repository: `akordonald15-hue/realityng-frontend`
- Feature branch: `feature/sprint-10-inspection-workflow`
- Feature commit before integration: `5e5e7b64034d7a220318f2be11082fd331acba0e`
- Previous `main`: `6bd152388bd763f97f7e7cafb3a17e48c060e51b`
- Final `main`: `5e5e7b64034d7a220318f2be11082fd331acba0e`
- Merge method: fast-forward
- Push status: pushed to `origin/main`

## Backend Validation

Local validation used the project virtual environment with a SQLite override because Docker Desktop was unavailable locally.

- `ruff check .`: passed
- `python manage.py check`: passed
- `python manage.py makemigrations --check --dry-run`: passed
- `python manage.py migrate --noinput`: passed on clean local DB
- `python manage.py spectacular --validate`: passed with 0 errors and 7 existing enum naming warnings
- `pytest apps/inspections/tests -q`: 10 passed after the JSON report regression test
- `pytest -q`: 241 passed

Production validation on the VPS used PostgreSQL, Redis, MinIO, and the deployed Docker backend.

- `inspections.0001_initial`: applied
- Production migrations after final deploy: no migrations pending
- Django check inside backend container: passed
- Redis ping: passed
- PostgreSQL inspection tables: present
- MinIO buckets: present

## Frontend Validation

- `npm run lint`: passed
- `npm run typecheck`: passed
- `npm run test`: 37 test files passed, 68 tests passed
- `NEXT_PUBLIC_USE_MOCKS=true npm run build`: passed
- `NEXT_PUBLIC_USE_MOCKS=false NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1 npm run build`: passed

Production route checks:

- `https://www.realityng.com`: 200
- `https://www.realityng.com/dashboard/inspections`: 200
- `https://www.realityng.com/admin/inspections`: 200

## Deployment

Backend deployment directory:

- `/opt/realityng/backend`

Deployed backend release marker:

- `4e32b7b83992ef8a4b30991853a9e6f326ade1c9`

RealityNG containers after deployment:

- `realityng-backend-1`: healthy
- `realityng-postgres-1`: healthy
- `realityng-redis-1`: healthy
- `realityng-minio-1`: healthy

Only the RealityNG backend container was intentionally recreated for the final backend release. RealityNG MinIO was recreated once during bucket initialization validation because the production compose file now includes the MinIO service and storage initializer. Caretekk was not restarted or modified.

## Storage

Sprint 10 storage buckets are configured through environment variables and initialized by the compose MinIO setup:

- Walkthrough videos: public media bucket for approved public videos.
- Inspection evidence: private bucket.
- Inspection reports: private bucket.

Validated buckets:

- `realityng-media`
- `realityng-verification-private`
- `realityng-walkthroughs`
- `realityng-inspection-evidence`
- `realityng-inspection-reports`

Private inspection evidence access is available only through backend-authorized signed URLs.

## Permission Policy

Walkthrough upload policy was resolved conservatively:

- Admins may upload/moderate walkthroughs.
- Actual property owners may upload walkthroughs when they hold an approved landlord or agent role.
- Role name alone is not enough for non-owner access.
- Verified property managers and assigned agents are deferred until the property model has explicit assignment/management relationships.

This prevents accidental privilege expansion.

## Production Smoke Test

A synthetic production smoke test was run inside the deployed backend container and cleaned up all synthetic records.

Validated:

- Owner walkthrough upload permission: passed
- Non-owner walkthrough upload denial: passed
- Public walkthrough list before approval: hidden
- Walkthrough submit, admin approve, public display: passed
- Admin hide, public removal: passed
- Customer inspection request creation: passed
- Cross-user request access denied as 404: passed
- Admin approval and inspector assignment: passed
- Inspector assignment list and accept: passed
- Inspection schedule and start: passed
- JSON inspection report creation: passed
- Evidence upload: passed
- Report submit and admin approve: passed
- Customer report retrieval by inspection request: passed
- Customer evidence signed URL: passed
- Inspection/walkthrough audit events: present
- Synthetic users/properties/walkthroughs/requests left behind: 0

Final smoke result:

```text
SMOKE_PASS=True
```

## Infrastructure Health

Post-deployment checks:

- RealityNG API health: `200`
- Caretekk API health: `200`
- Nginx config: valid
- RAM: 3.7 GiB total, 1.7 GiB used, 2.1 GiB available
- Swap: 6.0 GiB total, 1.7 GiB used
- Disk `/`: 75G total, 24G used, 48G available

Container restart counts:

- `realityng-backend-1`: 0
- `realityng-postgres-1`: 0
- `realityng-redis-1`: 0
- `realityng-minio-1`: 0
- `telehealthapp-nginx-1`: 0
- `telehealthapp-web-1`: 0
- `telehealthapp-asgi-1`: 0

Known unchanged warning:

- `/app/staticfiles/` directory warning appears in backend logs. It is unchanged and non-blocking for API operation.

## Rollback Assets

Existing rollback assets preserved:

- `/opt/realityng/backups/sprint10-20260805-180737`
- `/root/telehealthapp/nginx/default.conf.realityng-s67-backup-20260727-134949`

Additional backend rollback directories were created during deployment:

- `/opt/realityng/backend.previous-sprint10-jsonfix-*`
- `/opt/realityng/backend.replaced-sprint10-jsonfix-*`

Rollback approach:

1. Restore the previous backend directory.
2. Restore the previous `.release-commit`.
3. Recreate only `realityng-backend-1`.
4. Run `docker compose -p realityng ps`.
5. Confirm `https://api.realityng.com/api/v1/health/` and `https://api.caretekk.com/health/` return 200.

## Known Follow-Ups

- Staticfiles directory warning should be cleaned up in a future deployment polish task.
- Property-manager and assigned-agent walkthrough upload should be implemented only after explicit property assignment/management relationships exist.
- Full browser QA should continue during normal product acceptance, although production route and backend smoke checks passed.
- Heavy load testing remains out of scope for the shared production VPS.

## Final Verdict

✅ SPRINT 10 FULLY COMPLETE — DEPLOYMENT AND SMOKE TESTS PASSED
