# RealityNG Sprint 5.5 Security Audit Report

Date: 2026-07-09

## 1. Summary

Sprint 5.5 reviewed the backend, frontend, Docker local stack, environment handling, demo-mode boundary, object-level permissions, upload validation, audit logging, and dependency posture before Sprint 6.

Implemented fixes focused on high-value hardening without changing product scope:

- Added DRF throttling for authentication, registration, password reset, inquiry creation, viewing creation, rental application creation, and property image uploads.
- Hardened property image validation with MIME type, extension, file size, and image-content verification.
- Added a local SQLite cache fallback so host-side security tests do not require Redis while Docker/local production-like paths still use Redis.
- Changed frontend `.env.example` so mock mode is not the default.
- Added a visible demo-mode notice on sign-in without exposing demo credentials.
- Added regression tests for throttling configuration, cross-user activity-feed isolation, and upload validation.

## 2. Files Reviewed

Backend:

- `config/settings/base.py`
- `config/settings/local.py`
- `config/settings/production.py`
- `apps/accounts/views.py`
- `apps/accounts/serializers.py`
- `apps/accounts/permissions.py`
- `apps/properties/views.py`
- `apps/properties/serializers.py`
- `apps/properties/models.py`
- `apps/properties/permissions.py`
- `apps/properties/services.py`
- `docker-compose.yml`
- `.env.example`

Frontend:

- `.env.example`
- `src/lib/demo-mode.ts`
- `src/lib/api/*`
- `src/lib/auth/token-storage.ts`
- `src/mocks/*`
- `src/providers/auth-provider.tsx`
- `src/components/auth/protected-route.tsx`
- `src/app/auth/sign-in/page.tsx`
- Dashboard, property, inquiry, viewing, application, and saved-property pages/tests.

## 3. Vulnerabilities Found

- Sensitive API flows had no scoped rate limiting. This affected login, registration, password reset, inquiry creation, viewing creation, application submission, and image uploads.
- Property image upload validation relied on content type and size, but did not explicitly validate allowed extensions or verify uploaded image content in the serializer.
- Host-side local tests used Redis throttling cache when SQLite was selected, making security tests dependent on Docker DNS.
- Frontend `.env.example` defaulted `NEXT_PUBLIC_USE_MOCKS=true`, which is convenient for demos but unsafe as a default production posture.
- Demo sign-in did not clearly state that mock mode was active.
- Frontend dependency audit reports unresolved advisories in Next/PostCSS and Vitest/Vite/esbuild. npm recommends forced major/breaking upgrades, so these were documented instead of blindly upgraded.

## 4. Fixes Implemented

- Added `DEFAULT_THROTTLE_CLASSES` and scoped `DEFAULT_THROTTLE_RATES` in `config/settings/base.py`.
- Added `ScopedRateThrottle` to auth views in `apps/accounts/views.py`.
- Added action-scoped throttling to property upload, inquiry, viewing, and rental application create paths in `apps/properties/views.py`.
- Added `PROPERTY_IMAGE_ALLOWED_EXTENSIONS` setting and environment examples.
- Updated `PropertyImageSerializer.validate_image` to enforce allowed MIME types, allowed extensions, max size, and Pillow image verification.
- Added SQLite local-cache fallback in `config/settings/local.py`.
- Updated frontend `.env.example` to default `NEXT_PUBLIC_USE_MOCKS=false`.
- Added a demo-only sign-in notice while keeping mock credentials off the auth page.

## 5. Risks Remaining

- Frontend JWT tokens are still stored in `localStorage`. This is acceptable for the current sprint baseline but should move to an HTTP-only cookie/BFF strategy before production backend launch.
- Local Docker compose exposes Postgres, Redis, MinIO, and MinIO console ports to the host and uses local-only default credentials. This remains acceptable for local development only.
- MinIO local bucket is configured for anonymous download in the development compose file. Production storage must use private buckets and signed URLs where appropriate.
- `pip-audit` is not installed in the backend virtual environment, so Python dependency auditing could not run from the current environment.
- `npm audit` reports dependency advisories requiring breaking upgrades. These should be handled in a dedicated dependency upgrade sprint or patch window.

## 6. Recommended Production Security Checklist

- Set `DJANGO_SETTINGS_MODULE=config.settings.production`.
- Use a strong `SECRET_KEY` from a secret manager.
- Set exact `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and `CSRF_TRUSTED_ORIGINS`.
- Keep `SECURE_SSL_REDIRECT=true`, secure cookies, HSTS, `SECURE_CONTENT_TYPE_NOSNIFF`, and `X_FRAME_OPTIONS=DENY`.
- Use managed Postgres and Redis with private networking.
- Use private object storage buckets and signed media URLs.
- Rotate MinIO/S3 credentials away from local defaults.
- Disable `NEXT_PUBLIC_USE_MOCKS` in production frontend environments.
- Move access/refresh token storage away from browser `localStorage` before production backend launch.
- Add CI dependency audits with reviewed upgrade policy.
- Add production rate-limit monitoring and alerting.

## 7. Tests Added

- `apps/properties/tests/test_security_hardening.py`
  - Verifies sensitive endpoint throttle scopes.
  - Verifies dashboard activity feed hides unrelated user events.
- `apps/properties/tests/test_images_api.py`
  - Adds disallowed-extension upload test.
  - Adds invalid-image-content upload test.
- `src/app/auth/sign-in/sign-in-page.test.tsx`
  - Verifies demo-mode notice is visible.
  - Verifies demo credentials are not rendered.

## 8. Validation Results

Backend:

- `ruff check .`: passed.
- `python manage.py check`: passed.
- `python manage.py makemigrations --check --dry-run`: passed, no changes detected.
- `python manage.py migrate --noinput`: passed, no migrations to apply.
- `python manage.py spectacular --validate --file schema.yml`: passed.
- Security/media/dashboard focused tests: 15 passed.
- Inquiry API focused tests: 9 passed.
- Viewing API focused tests: 10 passed.
- Rental application API focused tests: 12 passed.
- `docker compose config -q`: passed.
- `python -m pip_audit`: not available; module not installed.

Frontend:

- `npm run lint`: passed.
- `npm run typecheck`: passed.
- `npm run test`: passed, 23 tests.
- `NEXT_PUBLIC_USE_MOCKS=true npm run build`: passed.
- `NEXT_PUBLIC_USE_MOCKS=false NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1 npm run build`: passed.
- `npm audit --omit=dev --audit-level=moderate`: reported 2 moderate production advisories in Next/PostCSS.
- `npm audit --audit-level=moderate`: reported dev and production advisories requiring breaking upgrades.

## 9. Git Commits

Commits are recorded in the backend and frontend repositories for Sprint 5.5 hardening.
