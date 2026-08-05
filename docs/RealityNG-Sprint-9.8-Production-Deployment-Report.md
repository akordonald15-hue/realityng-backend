# RealityNG Sprint 9.8 Production Deployment Report

## Executive Summary

Sprint 9.1 through Sprint 9.7 has been deployed to the shared production VPS safely.

The RealityNG backend is now running the Sprint 9 release runtime commit:

```text
c2b9c62617e9666512a5b5c636715024b217c5ac
```

The production API is healthy, the frontend is reachable through Vercel, database migrations completed, lightweight smoke tests passed, runtime monitoring remained stable for more than 15 minutes, and Caretekk remained healthy throughout.

No heavy load testing was performed. No Caretekk services were restarted. No shared Nginx routing changes were made.

## Production Environment

Shared VPS:

- Provider: Hetzner
- Shared applications: RealityNG and Caretekk
- Shared infrastructure: Docker, Nginx, PostgreSQL, Redis, MinIO, Cloudflare

RealityNG production endpoints:

- Backend API: `https://api.realityng.com/api/v1`
- Health endpoint: `https://api.realityng.com/api/v1/health/`
- Frontend: `https://www.realityng.com`

Caretekk health endpoint:

- `https://api.caretekk.com/health/`

## Pre-Deployment Audit

Before deployment:

- RealityNG API health returned `200`
- Caretekk health returned `200`
- RealityNG backend was running previous release marker `f6f29ab0219700b9f1b1c4544d3b17a8db1f3365`
- RealityNG containers were healthy:
  - `realityng-backend-1`
  - `realityng-postgres-1`
  - `realityng-redis-1`
  - `realityng-minio-1`
- Caretekk containers were running and unchanged
- Disk usage was approximately `34%`
- Memory available was approximately `2.0 GiB`
- Swap usage was approximately `1.7 GiB` and remained stable
- Shared Docker network `shared-proxy` existed
- Nginx configuration was not modified

Observed existing shared-network members:

- `telehealthapp-nginx-1`
- `realityng-backend-1`
- `realityng-minio-1`

Note: `realityng-minio-1` was already attached to `shared-proxy` before Sprint 9.8. It was not changed during this deployment.

## Backup Summary

Rollback directory:

```text
/opt/realityng/backups/release-s9.8-20260805-135311
```

Previous backend release directory:

```text
/opt/realityng/backend.previous-s9.8-20260805-135444
```

Backups created and verified:

- PostgreSQL dump: `realityng-postgres.sql`
- Current backend release directory
- Current backend `.env.production`
- Docker Compose files
- Current release marker
- Docker container inventory
- Docker stats snapshot
- Memory and disk snapshots
- Shared Docker network inspection
- Telehealth/Carettekk Nginx `default.conf`
- Telehealth/Caretekk production Compose file
- RealityNG MinIO data volume archive

Verification:

- PostgreSQL dump existed and was non-empty
- Backend env and Compose files existed in backup
- MinIO archive passed gzip integrity check

No secrets are included in this report.

## Backend Deployment

Deployment method:

- Local backend `main` was archived with `git archive`
- Artifact uploaded to the VPS
- Existing `/opt/realityng/backend` was moved aside
- New artifact was extracted into `/opt/realityng/backend`
- Existing `.env.production` was restored from backup
- `.release-commit` was set to `c2b9c62617e9666512a5b5c636715024b217c5ac`
- Docker Compose configuration was validated
- Only `realityng-backend-1` was rebuilt/recreated

Services not restarted:

- `realityng-postgres-1`
- `realityng-redis-1`
- `realityng-minio-1`
- `telehealthapp-*`
- `telehealthapp-nginx-1`

Backend container status after deployment:

```text
realityng-backend-1 Up healthy
```

## Migration Summary

Production migrations completed successfully.

New migrations applied during this deployment:

- `properties.0008_property_display_location_property_geocoding_status_and_more`
- `services.0001_initial`
- `services.0002_seed_trade_categories`
- `services.0003_portfolioimage_servicearea_is_primary_and_more`
- `services.0004_quoterequest`
- `services.0005_servicebooking`
- `services.0006_serviceprovider_average_communication_rating_and_more`
- `services.0007_providerappeal_servicecomplaint_and_more`

Django system check after deployment:

```text
System check identified no issues (0 silenced).
```

## Frontend Deployment

Frontend `main` had already been pushed and is reachable through Vercel.

Verified production frontend routes:

- `/`
- `/services`
- `/properties`
- `/dashboard`
- `/admin/services`
- `/dashboard/artisan/complaints`
- `/dashboard/artisan/appeals`

All checked routes returned:

```text
HTTP 200
Server: Vercel
```

The Vercel deployment metadata available from public headers confirmed Vercel serving, but public headers do not expose the Git commit. No Vercel settings were changed during this task.

## Smoke Test Results

Smoke testing was intentionally lightweight and serial. No load, stress, or concurrency testing was performed.

Public checks:

- Frontend homepage: `200`
- API health: `200`
- Public property listing: `200`
- Service categories: `200`
- Service provider listing: `200`
- Assistant config: `200`
- CORS preflight from `https://www.realityng.com`: `200`
- Unauthorized customer dashboard: `401`
- Unauthorized admin dashboard: `401`

Authentication:

- Registration: `201`
- Login: `200`
- Authenticated profile: `200`
- Token refresh: `200`
- Logout: `204`

Assistant:

- Assistant config returned:
  - `enabled: true`
  - `provider_mode: demo`
  - `label: RealityNG Demo Assistant`
- Supported demo topics were returned correctly.

Services fixture smoke:

A temporary synthetic provider/customer/admin fixture was created and removed after testing.

Validated:

- Public provider profile: `200`
- Quote request submission: `201`
- Provider quote-request list: `200`
- Provider dashboard: `200` after adding approved artisan role to the synthetic provider
- Review submission for completed booking: `201`
- Customer review list: `200`
- Complaint submission: `201`
- Customer complaints list: `200`
- Admin services dashboard: `200`
- Admin providers queue: `200`
- Admin complaints queue: `200`
- Admin reviews queue: `200`

Cleanup:

- Synthetic provider removed
- Synthetic trade removed
- Synthetic service area removed
- Synthetic quote request removed
- Synthetic completed booking removed
- Synthetic review removed
- Synthetic complaint removed
- Synthetic users removed
- Post-cleanup residue check:
  - `s98_users = 0`
  - `s98_providers = 0`

## Runtime Verification

Runtime checks:

- Backend health remained `200`
- Caretekk health remained `200`
- Nginx config validation passed
- No new backend error, exception, traceback, storage, permission, or migration errors appeared in recent backend logs
- One unrelated older Caretekk staging Nginx timeout was visible in Nginx logs from earlier in the day; it was not caused by this deployment

Nginx validation:

```text
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

## Resource Monitoring

Monitoring window:

- Backend observed healthy for more than 15 minutes after recreation

Final sample:

- `realityng-backend-1`: approximately `111.7 MiB / 512 MiB`
- `realityng-postgres-1`: approximately `33.27 MiB / 512 MiB`
- `realityng-redis-1`: approximately `1.637 MiB / 128 MiB`
- `realityng-minio-1`: approximately `119.2 MiB / 256 MiB`
- System memory available: approximately `2.0 GiB`
- Swap used: approximately `1.7 GiB`
- Disk usage: approximately `34%`

Restart counts checked:

- `realityng-backend-1`: `0`
- `realityng-postgres-1`: `0`
- `realityng-redis-1`: `0`
- `realityng-minio-1`: `0`
- `telehealthapp-nginx-1`: `0`
- `telehealthapp-web-1`: `0`

## Regression Summary

Verified directly or through smoke coverage:

- Authentication
- Public property listing
- Services marketplace public browse
- Provider profile
- Quote requests
- Customer services dashboard
- Provider services dashboard
- Admin services dashboard
- Reviews
- Complaints
- Assistant demo configuration
- Maps fallback route availability through frontend
- Frontend dashboard/admin routes
- Caretekk health

No regression was observed during the production smoke window.

## Rollback Readiness

Rollback readiness confirmed:

- Current backup exists
- Previous backend release directory exists
- Previous release commit is documented
- PostgreSQL dump exists
- Environment backup exists
- Compose backup exists
- Nginx backup exists
- MinIO data archive exists
- Rollback guide exists in `docs/RealityNG-Rollback-Guide.md`

Rollback was not executed.

## Known Issues and Follow-Ups

Known operational follow-ups:

- Production Google Maps activation remains deferred until Google Cloud billing and a restricted production API key are approved.
- Public Vercel headers do not expose the deployed Git commit, so frontend deployment commit was verified by route availability rather than public commit metadata.
- The shared VPS should not be used for load testing.
- A staging or temporary VPS should be used for k6, Locust, or Artillery performance validation.
- Existing RealityNG MinIO is attached to the shared proxy network. This was pre-existing and unchanged; review whether this should be narrowed in a future infrastructure hardening window.

## Production Recommendation

Sprint 9 production deployment is successful.

RealityNG is stable after deployment, Caretekk remains unaffected, smoke tests passed, runtime monitoring is stable, and rollback readiness is confirmed.

Final verdict:

```text
✅ SPRINT 9 FULLY COMPLETE — PRODUCTION DEPLOYMENT SUCCESSFUL
```

