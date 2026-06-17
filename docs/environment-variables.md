# RealityNG Backend Environment Variables

## Required Local Variables

| Variable | Example | Purpose |
| --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.local` | Selects Django settings module. |
| `SECRET_KEY` | `change-me` | Django signing secret. Use a strong private value outside local development. |
| `DEBUG` | `true` | Enables local debug behavior. Must be `false` in production. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,backend` | Hosts Django will serve. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Frontend origins allowed to call the API. |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Trusted origins for cookie-authenticated unsafe requests. |
| `DATABASE_URL` | `postgres://realityng:realityng@postgres:5432/realityng` | PostgreSQL connection string. |
| `REDIS_URL` | `redis://redis:6379/0` | Redis cache URL. |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Celery broker URL. |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` | Celery result backend URL. |
| `MINIO_ENDPOINT` | `http://minio:9000` | S3-compatible local object storage endpoint. |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key. |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key. |
| `MINIO_BUCKET_NAME` | `realityng-local` | Local object storage bucket name. |

## Optional Variables

| Variable | Example | Purpose |
| --- | --- | --- |
| `SENTRY_DSN` | empty locally | Enables Sentry when populated. |
| `SENTRY_ENVIRONMENT` | `local` | Sentry environment tag. |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.0` | Sentry tracing sample rate. |
| `LANDLORD_ROLE_AUTO_APPROVAL` | `true` | Controls whether landlord role requests are automatically approved for MVP. |

## Production Variables

| Variable | Purpose |
| --- | --- |
| `SECURE_SSL_REDIRECT` | Forces HTTPS in production. |
| `SECURE_HSTS_SECONDS` | HSTS duration in production. |
| `EMAIL_HOST` | SMTP host. |
| `EMAIL_PORT` | SMTP port. |
| `EMAIL_HOST_USER` | SMTP username. |
| `EMAIL_HOST_PASSWORD` | SMTP password. |
| `EMAIL_USE_TLS` | SMTP TLS toggle. |
| `DEFAULT_FROM_EMAIL` | Transactional email sender. |

## Security Notes

1. Never commit real `.env` files.
2. Rotate `SECRET_KEY`, database credentials, MinIO/S3 credentials, and Sentry DSNs per environment.
3. Production should use managed secret storage instead of plaintext environment files.
