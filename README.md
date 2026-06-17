# RealityNG Backend

Django REST Framework backend for RealityNG, a diaspora-focused Nigerian PropTech platform.

This repository contains the backend foundation for RealityNG. Sprint 1 adds authentication, roles, user profiles, JWT sessions, role approval workflows, reusable permissions, and audit logs for role requests.

## Repository Structure

```text
.
|-- apps/
|   |-- common/          # Shared abstract model primitives
|   `-- core/            # Health endpoint, request IDs, logging
|-- config/
|   |-- settings/        # base.py, local.py, production.py
|   |-- celery.py
|   |-- urls.py
|   |-- asgi.py
|   `-- wsgi.py
|-- docs/
|   `-- environment-variables.md
|-- requirements/
|-- .github/workflows/
|-- docker-compose.yml
|-- Dockerfile
|-- manage.py
|-- pyproject.toml
`-- pytest.ini
```

## Prerequisites

Install:

1. Docker Desktop
2. Python 3.12 if running without Docker

## Local Setup With Docker

From the repository root:

```powershell
docker compose up --build
```

Services:

1. Backend API: http://localhost:8000
2. Health endpoint: http://localhost:8000/api/v1/health/
3. API docs: http://localhost:8000/api/docs/
4. Django admin: http://localhost:8000/admin/
5. MinIO API: http://localhost:9000
6. MinIO console: http://localhost:9001

Default MinIO credentials:

```text
Username: minioadmin
Password: minioadmin
```

## Local Setup Without Docker

Start PostgreSQL and Redis locally, then:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements\local.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py runserver
```

Run Celery worker:

```powershell
celery -A config.celery worker --loglevel=INFO
```

Run Celery Beat:

```powershell
celery -A config.celery beat --loglevel=INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## Environment Variables

Copy the example:

```powershell
Copy-Item .env.example .env
```

See [docs/environment-variables.md](docs/environment-variables.md) for the full variable reference.

## Tests and Linting

```powershell
pytest
ruff check .
```

## API Documentation

DRF Spectacular exposes:

1. Schema: http://localhost:8000/api/schema/
2. Swagger UI: http://localhost:8000/api/docs/

Sprint 1 endpoints are included under `/api/v1/auth/`, `/api/v1/users/`, `/api/v1/roles/`, and `/api/v1/admin/role-requests/`.

## Authentication Flow

1. A user registers through `POST /api/v1/auth/register/`.
2. The backend creates a custom UUID user and `UserProfile`.
3. The user signs in through `POST /api/v1/auth/login/`.
4. The login response returns `access`, `refresh`, and the serialized user.
5. Clients send `Authorization: Bearer <access>` on authenticated requests.
6. Clients refresh sessions through `POST /api/v1/auth/token/refresh/`.
7. Logout blacklists the refresh token through `POST /api/v1/auth/logout/`.

Suspended users cannot log in and existing JWT access is denied by the custom JWT authentication class.

Password reset endpoints are available as a foundation:

1. `POST /api/v1/auth/forgot-password/`
2. `POST /api/v1/auth/reset-password/`

Email verification and phone verification fields exist on the user model; delivery workflows are intentionally left for a later sprint.

## Role Approval Flow

Seeded roles:

1. `tenant`
2. `buyer`
3. `landlord`
4. `agent`
5. `artisan`
6. `lawyer`
7. `inspector`
8. `admin`
9. `super_admin`

Flow:

1. Authenticated users list roles through `GET /api/v1/roles/`.
2. Users request roles through `POST /api/v1/roles/request/`.
3. `tenant`, `buyer`, and MVP `landlord` requests are auto-approved.
4. `agent`, `artisan`, `lawyer`, and `inspector` requests remain pending until admin approval.
5. `admin` and `super_admin` cannot be self-assigned.
6. Admins review pending requests through `GET /api/v1/admin/role-requests/`.
7. Admins approve or reject through the role request decision endpoints.
8. Role request and decision actions create audit logs.

`LANDLORD_ROLE_AUTO_APPROVAL=true` controls landlord auto-approval and can be changed later without changing API contracts.

## Database Foundation

The foundation establishes:

1. PostgreSQL connection configuration through `DATABASE_URL`.
2. UUID primary key convention via `UUIDPrimaryKeyMixin`.
3. `TimestampMixin` with `created_at` and `updated_at`.
4. `SoftDeleteMixin` with `deleted_at`, soft-delete queryset behavior, and hard-delete escape hatch.
5. Initial migrations strategy: Django built-in apps and third-party migrations only until Sprint 1 introduces domain models.

Sprint 1 adds only authentication, role, profile, and role-audit entities. Property marketplace entities remain out of scope until Sprint 2.

## Monitoring and Logging

Backend logs are structured JSON and include a request correlation ID when available.

To enable Sentry:

```text
SENTRY_DSN=<your-dsn>
SENTRY_ENVIRONMENT=local|staging|production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

## CI

GitHub Actions runs:

1. Python dependency installation.
2. `ruff check .`
3. `pytest`

The workflow starts PostgreSQL and Redis service containers for tests.

## Troubleshooting

Docker ports already in use:

1. Stop services using ports `8000`, `5432`, `6379`, `9000`, or `9001`.
2. Or change the published ports in `docker-compose.yml`.

Reset local Docker database:

```powershell
docker compose down -v
docker compose up --build
```

Backend cannot connect to Postgres:

1. Confirm the `postgres` service is healthy.
2. Use host `postgres` inside Docker and `localhost` outside Docker.

Celery cannot connect:

1. Confirm Redis is healthy.
2. Confirm `CELERY_BROKER_URL` points to Redis.

## Manual Steps Before Sprint 1

## Manual Steps Before Sprint 2

1. Apply migrations after pulling Sprint 1:

```powershell
python manage.py migrate
```

2. Create a superuser when needed:

```powershell
docker compose exec backend python manage.py createsuperuser
```

3. Confirm `LANDLORD_ROLE_AUTO_APPROVAL` is correct for the target environment.

