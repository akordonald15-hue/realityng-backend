# RealityNG Backend

Django REST Framework backend for RealityNG, a diaspora-focused Nigerian PropTech platform.

This repository contains the RealityNG backend through Sprint 9.1 foundations. It includes authentication and roles, property listing CRUD and moderation, public browsing, property galleries, favorites, inquiries, viewings, rental applications, verification workflows, the guided assistant framework, dashboard summaries, apartment-share listing support, location-intelligence fields for privacy-safe map discovery, and the verified services marketplace foundation.

## Repository Structure

```text
.
|-- apps/
|   |-- common/          # Shared abstract model primitives
|   |-- properties/      # Property listings, review workflow, media, public browse API
|   |-- services/        # Verified services marketplace foundation
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

Sprint 2 property endpoints are included under `/api/v1/properties/` and `/api/v1/public/properties/`.

Sprint 3 property image endpoints are nested under `/api/v1/properties/{slug}/images/`.

Sprint 8 extends property responses with privacy-safe location metadata for map/list discovery. Public responses expose rounded or hidden coordinates according to each property's location precision. Exact private coordinates remain available only through owner/admin workflows where permitted.

Sprint 9.1 service marketplace endpoints are included under `/api/v1/services/categories/`, `/api/v1/services/providers/`, and `/api/v1/services/providers/{slug}/`. Public responses expose active providers, public service areas, trade categories, and verification badge snapshots only. Private addresses, verification documents, and internal moderation fields are not serialized.

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
6. `inspector`
7. `admin`
8. `super_admin`

Flow:

1. Authenticated users list roles through `GET /api/v1/roles/`.
2. Users request roles through `POST /api/v1/roles/request/`.
3. `tenant`, `buyer`, and MVP `landlord` requests are auto-approved.
4. `agent`, `artisan`, and `inspector` requests remain pending until admin approval.
5. `admin` and `super_admin` cannot be self-assigned.
6. Admins review pending requests through `GET /api/v1/admin/role-requests/`.
7. Admins approve or reject through the role request decision endpoints.
8. Role request and decision actions create audit logs.

`LANDLORD_ROLE_AUTO_APPROVAL=true` controls landlord auto-approval and can be changed later without changing API contracts.

## Property Listing Flow

Authenticated users can create draft listings through `POST /api/v1/properties/`.

Owner/admin management endpoints:

1. `GET /api/v1/properties/`
2. `POST /api/v1/properties/`
3. `GET /api/v1/properties/{slug}/`
4. `PATCH /api/v1/properties/{slug}/`
5. `DELETE /api/v1/properties/{slug}/`
6. `POST /api/v1/properties/{slug}/submit-for-review/`
7. `POST /api/v1/properties/{slug}/approve/`
8. `POST /api/v1/properties/{slug}/reject/`

Public browsing endpoints:

1. `GET /api/v1/public/properties/`
2. `GET /api/v1/public/properties/{slug}/`

Public browsing returns approved listings only and supports:

1. Pagination
2. Ordering by `created_at`, `price`, `title`, and `featured`
3. Search by title through `search`
4. Filters for `city`, `property_type`, `listing_type`, `min_price`, and `max_price`

Supported listing types are `sale`, `rent`, and `apartment_share`. Apartment-share listings must use the apartment property type.

Listings are soft-deleted through the shared `SoftDeleteMixin`. Updating an approved listing moves it back to `draft` so it can be reviewed again.

## Property Media Flow

Owner/admin image endpoints:

1. `GET /api/v1/properties/{slug}/images/`
2. `POST /api/v1/properties/{slug}/images/`
3. `PATCH /api/v1/properties/{slug}/images/{image_id}/`
4. `DELETE /api/v1/properties/{slug}/images/{image_id}/`
5. `POST /api/v1/properties/{slug}/images/{image_id}/set-cover/`

Rules:

1. Owners can manage images for their own properties.
2. Admin users can manage images for any property.
3. Non-owners cannot manage property images.
4. A property can have up to `PROPERTY_IMAGE_MAX_COUNT` images.
5. Accepted MIME types are configured through `PROPERTY_IMAGE_ALLOWED_TYPES`.
6. Maximum file size is configured through `PROPERTY_IMAGE_MAX_SIZE_MB`.
7. Only one image can be cover at a time.

Docker local development uses MinIO when `USE_S3_MEDIA_STORAGE=true`; non-Docker local tests default to Django filesystem media storage. Public property responses include `cover_image_url`, `image_count`, and `image_gallery`.

## Database Foundation

The foundation establishes:

1. PostgreSQL connection configuration through `DATABASE_URL`.
2. UUID primary key convention via `UUIDPrimaryKeyMixin`.
3. `TimestampMixin` with `created_at` and `updated_at`.
4. `SoftDeleteMixin` with `deleted_at`, soft-delete queryset behavior, and hard-delete escape hatch.
5. Initial migrations strategy: Django built-in apps and third-party migrations only until Sprint 1 introduces domain models.

Sprint 1 adds authentication, role, profile, and role-audit entities. Sprint 2 adds the `Property` entity with indexes for status, location, type/listing filters, price, owner/status, and slug lookup. Sprint 3 adds `PropertyImage` with property/order and cover-image indexes plus a conditional unique constraint for one cover image per property.

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

## Manual Steps Before Sprint 4

1. Apply migrations after pulling Sprint 3:

```powershell
python manage.py migrate
```

2. Create a superuser when needed:

```powershell
docker compose exec backend python manage.py createsuperuser
```

3. Confirm default Docker host ports are free, or use alternate published ports when another stack is running locally.
4. Confirm `LANDLORD_ROLE_AUTO_APPROVAL` is correct for the target environment.
5. Confirm `MINIO_PUBLIC_ENDPOINT` matches the browser-accessible object storage URL for the target environment.
