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

Status: FAIL

- Compose configuration validation passed for the root compose file.
- Compose configuration validation passed for the backend compose file.
- Initial validation failed because the Docker Desktop Linux engine pipe was unavailable.
- Rerun after Docker Desktop was started still failed because Docker Desktop remained in `starting` status and the Docker API returned HTTP 500.
- `docker compose build` failed before image builds could complete.
- `docker compose up -d` failed before services could start.
- `docker compose ps` could not verify service health because the Docker daemon API remained unhealthy.

Observed Docker errors:

```text
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
request returned 500 Internal Server Error for API route and version http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.51/images/realityng-celery/json, check if the server supports the requested API version
```

Observed Docker Desktop status on rerun:

```text
Status starting
```

Services not verified due to Docker daemon failure:

- frontend
- backend
- postgres
- redis
- celery
- celery-beat
- minio

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

## Remaining Risks

- Docker runtime validation is blocked until Docker Desktop finishes starting and the Docker daemon API responds successfully.
- Service health checks for frontend, backend, postgres, redis, celery, celery-beat, and minio remain unverified.
- The Whitenoise `staticfiles/` warning is harmless for this gate but should be eliminated before production hardening by ensuring static collection paths exist in runtime environments.

## Final Status

FAIL

Sprint 1 cannot be marked complete because Docker services did not start and service health could not be verified. All non-Docker validation gates passed.

Do not proceed to Sprint 2 until Docker build, Docker startup, and Docker health verification pass.
