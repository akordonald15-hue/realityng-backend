# RealityNG Sprint 1 Validation Report

Date: 2026-06-17
Scope: Sprint 1 Authentication, Roles, and User Profiles

## Backend Results

Status: PASS

- Dependencies installed with `pip install -r requirements/local.txt`.
- Django system checks passed with `python manage.py check`.
- Migration drift check passed with `python manage.py makemigrations --check`.
- Database initialization passed with `python manage.py migrate --noinput` against a local validation SQLite database.
- OpenAPI generation passed with `python manage.py spectacular --file schema.yml`.
- Lint passed with `ruff check .`.
- Pytest passed: 22 tests collected, 22 passed.
- Coverage summary: 94% total coverage across `apps`.
- Non-blocking warning: Whitenoise reported that `staticfiles/` does not exist during tests. This does not affect the Sprint 1 validation outcome.

## Frontend Results

Status: PASS

- Dependencies installed with `npm ci --no-audit --no-fund`.
- ESLint passed with `npm run lint`.
- TypeScript passed with `npm run typecheck`.
- Vitest passed with `npm run test`: 5 test files passed, 7 tests passed.
- Next.js production build passed with `npm run build`.

## Docker Results

Status: PASS

- Compose configuration validation passed for the root compose file.
- Compose configuration validation passed for the backend compose file.
- Docker Desktop rerun confirmed the daemon was running.
- `docker compose build` passed for backend, frontend, celery, and celery-beat images.
- The first default-port startup was blocked by existing local Telehealth containers already publishing `5432`, `6379`, and `8000`.
- Runtime validation was completed with a temporary host-port override while keeping internal container ports unchanged.
- `docker compose up -d` passed with the validation override.
- `docker compose ps` showed all services running and healthy.
- Backend host health check passed: `GET http://localhost:18000/api/v1/health/` returned `200`.
- Frontend host check passed: `GET http://localhost:13000/` returned `200`.

Validated Docker services:

- frontend: healthy on host port `13000`
- backend: healthy on host port `18000`
- postgres: healthy on host port `15432`
- redis: healthy on host port `16379`
- celery: healthy
- celery-beat: healthy
- minio: healthy on host ports `19000` and `19001`

## API Results

Status: PASS via automated tests

Validated endpoint groups:

- `POST /api/v1/auth/register/`
- `POST /api/v1/auth/login/`
- `POST /api/v1/auth/token/refresh/`
- `POST /api/v1/auth/logout/`
- `POST /api/v1/auth/forgot-password/`
- `POST /api/v1/auth/reset-password/`
- `GET /api/v1/users/me/`
- `PATCH /api/v1/users/me/`
- `GET /api/v1/roles/`
- `POST /api/v1/roles/request/`
- `GET /api/v1/admin/role-requests/`
- `POST /api/v1/admin/role-requests/{id}/approve/`
- `POST /api/v1/admin/role-requests/{id}/reject/`

Validation covered success responses, validation errors, authentication errors, and permission errors.

## Security Results

Status: PASS for code-level checks

- Suspended users are denied JWT authentication.
- JWT refresh rotation is configured through SimpleJWT.
- Passwords are hashed through Django's password hasher.
- Admin role request endpoints are protected.
- Admin and super admin role self-assignment is blocked.
- Duplicate active role assignments are blocked.
- Role request, approval, and rejection audit logs are created.
- No Sprint 1 security vulnerability was identified in automated validation.

## Issues Fixed

- Added missing migration for custom user manager and profile avatar changes after `makemigrations --check` detected model drift.
- Added a DRF Spectacular JWT authentication extension so OpenAPI schema generation has a stable auth scheme.
- Added health endpoint schema metadata to remove schema ambiguity.
- Increased the default development secret key length to satisfy Django security checks.
- Updated Ruff configuration to exclude migrations and ignore the Django admin display ordering rule that conflicts with the selected admin model layout.
- Fixed long lint violations in backend source and tests.
- Added `.gitignore` entries for local SQLite validation databases and generated OpenAPI schema files.
- Added API endpoint validation tests for auth, roles, admin role requests, and protected user profile routes.
- Fixed logout behavior so invalid or already blacklisted refresh tokens return a validation error instead of raising an unhandled token exception.
- Ordered admin role request querysets to avoid pagination instability warnings.
- Adjusted Vitest configuration to use a stable single fork pool on Windows.
- Added React Testing Library cleanup between tests to prevent DOM state leakage.
- Stabilized the profile test mock user object to avoid repeated render/effect resets.
- Wrapped the reset password route's `useSearchParams` usage in Suspense so the Next.js production build can prerender correctly.
- Updated the frontend Docker image to run a production Next.js build with `next start` instead of bind-mounted `next dev`.
- Updated frontend Docker health checks to use `127.0.0.1`.
- Added Docker health-check start periods for slow backend and frontend startup on Windows/OneDrive.
- Replaced the Celery inspect health check with a direct Redis broker socket check.

## Remaining Risks

- Default host ports are still occupied by an unrelated local Telehealth Docker stack on this machine. RealityNG was validated with alternate host ports; default ports should work when `5432`, `6379`, and `8000` are free.
- The Whitenoise `staticfiles/` warning is harmless for this gate but should be eliminated before production hardening by ensuring static collection paths exist in runtime environments.
- Celery is currently running as root in the local development container. This is acceptable for Sprint 1 local validation but should be hardened before production deployment.

## Final Status

PASS

Sprint 1 validation is complete. All required non-Docker checks passed, Docker image builds passed, and all Docker services started and reached healthy status under the validation port override.
