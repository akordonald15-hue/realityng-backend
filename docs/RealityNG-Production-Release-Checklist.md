# RealityNG Production Release Checklist

## Purpose

This checklist prepares the Sprint 9 Services Marketplace release for a safe production deployment on the shared RealityNG and Caretekk VPS.

Production availability has priority. Do not perform stress testing on the shared VPS, do not restart Caretekk services, and do not change shared Nginx routing unless a deployment issue requires a narrowly scoped RealityNG-only fix.

## Release Scope

Sprint 9.1 through Sprint 9.7 includes:

- Service categories
- Provider profiles
- Provider trades
- Provider service areas
- Provider portfolios
- Quote requests
- Minimal service bookings for review eligibility
- Booking-linked reviews
- Rating aggregates
- Provider review responses
- Review flags
- Services dashboards
- Complaints
- Warnings
- Suspensions
- Appeals
- Admin moderation
- Release hardening and documentation

Out of scope for this deployment:

- Payments
- Escrow
- Real-time service chat
- Notification delivery
- Subscriptions
- Sponsored providers
- Heavy production load testing

## Required Production Environment

Backend:

- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`
- `CSRF_TRUSTED_ORIGINS`
- `AI_ASSISTANT_ENABLED=true`
- `AI_PROVIDER_MODE=demo`
- `VERIFICATION_DOCUMENT_BUCKET_NAME`
- `VERIFICATION_SIGNED_URL_EXPIRY`
- `SERVICE_COMPLAINT_EVIDENCE_MAX_SIZE_MB`
- `SERVICE_COMPLAINT_EVIDENCE_ALLOWED_TYPES`
- `SERVICE_COMPLAINT_EVIDENCE_ALLOWED_EXTENSIONS`
- Existing MinIO/S3 media settings

Frontend:

- `NEXT_PUBLIC_USE_MOCKS=false`
- `NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1`
- `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` only when Google Maps production activation is approved

Never add backend secrets such as database, Redis, MinIO secret, or AI provider credentials to frontend environment variables.

## Pre-Deployment Safety Checks

Run before changing production:

1. Confirm Caretekk health:
   ```bash
   curl -i https://api.caretekk.com/health/
   ```

2. Confirm RealityNG health:
   ```bash
   curl -i https://api.realityng.com/api/v1/health/
   ```

3. Record running containers:
   ```bash
   docker ps
   docker compose ls
   docker stats --no-stream
   free -h
   df -h
   ```

4. Confirm shared Nginx container remains running:
   ```bash
   docker ps --filter "name=telehealthapp-nginx-1"
   ```

5. Confirm RealityNG containers:
   ```bash
   docker compose -p realityng ps
   ```

6. Record currently deployed commits:
   ```bash
   cd /opt/realityng/backend
   git rev-parse HEAD
   ```

7. Confirm rollback assets exist before proceeding.

## Backup Checklist

Create a timestamped release backup directory:

```bash
mkdir -p /opt/realityng/backups/release-s9-$(date +%Y%m%d-%H%M%S)
```

Back up:

- Current backend `.env`
- Current production compose files
- Current deployed commit hash
- PostgreSQL database dump
- Current container/image list
- Current Nginx RealityNG virtual host configuration if it will be touched

PostgreSQL backup example:

```bash
docker compose -p realityng exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > /opt/realityng/backups/release-s9-YYYYMMDD-HHMMSS/realityng.sql
```

Do not back up or print secret values into the release report.

## Deployment Sequence

Backend deployment:

1. Deploy only RealityNG backend code from `main`.
2. Do not restart Caretekk.
3. Do not recreate PostgreSQL, Redis, MinIO, or Nginx unless strictly required.
4. Rebuild/recreate the backend service only:
   ```bash
   cd /opt/realityng/backend
   git fetch origin
   git checkout main
   git pull --ff-only origin main
   docker compose -p realityng -f docker-compose.yml -f compose.production.yaml up -d --no-deps --build backend
   ```

5. Run migrations:
   ```bash
   docker compose -p realityng -f docker-compose.yml -f compose.production.yaml exec backend python manage.py migrate --noinput
   ```

6. Run Django checks:
   ```bash
   docker compose -p realityng -f docker-compose.yml -f compose.production.yaml exec backend python manage.py check
   ```

Frontend deployment:

1. Deploy from frontend `main`.
2. Confirm production environment:
   ```env
   NEXT_PUBLIC_USE_MOCKS=false
   NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1
   ```
3. Verify the deployed commit matches frontend `main`.

## Post-Deployment Verification

Backend health:

```bash
curl -i https://api.realityng.com/api/v1/health/
```

Caretekk health:

```bash
curl -i https://api.caretekk.com/health/
```

RealityNG API smoke checks:

- Authentication register/login/logout
- Public property listing
- Public services categories
- Public providers listing
- Provider profile detail
- Quote request submission
- Customer services dashboard
- Provider services dashboard
- Admin services dashboard
- Complaint submission
- Appeal view
- Review listing
- Maps fallback without production Maps key

Frontend smoke checks:

- Homepage
- Properties
- Services
- Provider profile
- Sign in/sign up
- Dashboard entry
- Public demo assistant
- Mobile navigation

Infrastructure checks:

```bash
docker compose -p realityng ps
docker stats --no-stream
free -h
df -h
docker ps --filter "name=telehealthapp"
```

Confirm:

- RealityNG is healthy
- Caretekk remains healthy
- No Caretekk container restarted
- PostgreSQL, Redis, and MinIO remain private
- Nginx routing still works
- Swap is not increasing rapidly
- Disk remains within safe limits

## Rollback Trigger Conditions

Rollback if any of the following occur:

- RealityNG health endpoint fails after deployment
- Login or registration is broken
- Core property marketplace is unavailable
- Services provider listing is unavailable
- Migrations fail and cannot be corrected quickly
- Caretekk health check fails
- Nginx validation fails
- Containers enter restart loops
- Resource usage becomes unsafe

## Release Decision

Release may proceed only after:

- Backups are verified
- Backend migrations complete
- RealityNG health returns 200
- Frontend is reachable
- Caretekk remains healthy
- Smoke tests pass
- Rollback path is confirmed

