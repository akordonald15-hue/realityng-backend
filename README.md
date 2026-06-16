# RealityNG Backend

Django REST Framework backend for RealityNG, a diaspora-focused Nigerian PropTech platform.

This repository contains the Sprint 0 backend foundation: Django project structure, settings split, DRF, DRF Spectacular, Celery, Redis, PostgreSQL, MinIO, health checks, structured logging, request correlation IDs, pytest, and CI.

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

## Database Foundation

Sprint 0 establishes:

1. PostgreSQL connection configuration through `DATABASE_URL`.
2. UUID primary key convention via `UUIDPrimaryKeyMixin`.
3. `TimestampMixin` with `created_at` and `updated_at`.
4. `SoftDeleteMixin` with `deleted_at`, soft-delete queryset behavior, and hard-delete escape hatch.
5. Initial migrations strategy: Django built-in apps and third-party migrations only until Sprint 1 introduces domain models.

RealityNG domain entities are intentionally not implemented in Sprint 0.

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

1. Decide whether to keep Django's default `User` model or introduce a custom user model before the first production auth migration.
2. Create a superuser when needed:

```powershell
docker compose exec backend python manage.py createsuperuser
```

