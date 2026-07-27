# RealityNG Backend Environment Variables

## Required Local Variables

| Variable | Example | Purpose |
| --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.local` | Selects Django settings module. |
| `SECRET_KEY` | `change-me` | Django signing secret. Use a strong private value outside local development. |
| `ANTHROPIC_API_KEY` | empty locally | Enables the AI assistant when populated. Keep this value server-side only. |
| `ANTHROPIC_MODEL` | `claude-sonnet-5` | Anthropic model ID used by the assistant provider. |
| `DEBUG` | `true` | Enables local debug behavior. Must be `false` in production. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,backend` | Hosts Django will serve. |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Frontend origins allowed to call the API. |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Trusted origins for cookie-authenticated unsafe requests. |
| `SECURE_SSL_REDIRECT` | `false` | Redirects HTTP to HTTPS when enabled. Keep `false` for HTTP-only development environments. |
| `SESSION_COOKIE_SECURE` | `false` | Sends session cookies over HTTPS only when enabled. Keep `false` for HTTP-only development environments. |
| `CSRF_COOKIE_SECURE` | `false` | Sends CSRF cookies over HTTPS only when enabled. Keep `false` for HTTP-only development environments. |
| `DATABASE_URL` | `postgres://realityng:realityng@postgres:5432/realityng` | PostgreSQL connection string. |
| `REDIS_URL` | `redis://redis:6379/0` | Redis cache URL. |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Celery broker URL. |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/0` | Celery result backend URL. |
| `MINIO_ENDPOINT` | `http://minio:9000` | S3-compatible local object storage endpoint. |
| `MINIO_PUBLIC_ENDPOINT` | `http://localhost:9000` | Browser-accessible object storage endpoint used when generating media URLs. |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key. |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key. |
| `MINIO_BUCKET_NAME` | `realityng-local` | Local object storage bucket name. |
| `VERIFICATION_DOCUMENT_BUCKET_NAME` | `realityng-verification-private` | Private bucket for sensitive verification evidence. Do not make this bucket public. |
| `USE_S3_MEDIA_STORAGE` | `true` | Enables S3-compatible media storage. Docker local development sets this to `true`; direct local tests can leave it `false`. |

## Optional Variables

| Variable | Example | Purpose |
| --- | --- | --- |
| `SENTRY_DSN` | empty locally | Enables Sentry when populated. |
| `SENTRY_ENVIRONMENT` | `local` | Sentry environment tag. |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.0` | Sentry tracing sample rate. |
| `LANDLORD_ROLE_AUTO_APPROVAL` | `true` | Controls whether landlord role requests are automatically approved for MVP. |
| `PROPERTY_IMAGE_MAX_COUNT` | `30` | Maximum number of uploaded images per property. |
| `PROPERTY_IMAGE_MAX_SIZE_MB` | `10` | Maximum uploaded image size in megabytes. |
| `PROPERTY_IMAGE_ALLOWED_TYPES` | `image/jpeg,image/png,image/webp` | Comma-separated allowed image MIME types. |
| `VERIFICATION_DOCUMENT_MAX_SIZE_MB` | `10` | Maximum uploaded verification document size in megabytes. |
| `VERIFICATION_DOCUMENT_ALLOWED_TYPES` | `application/pdf,image/jpeg,image/png` | Comma-separated allowed verification document MIME types. |
| `VERIFICATION_DOCUMENT_ALLOWED_EXTENSIONS` | `.pdf,.jpg,.jpeg,.png` | Comma-separated allowed verification document extensions. |
| `VERIFICATION_SIGNED_URL_EXPIRY` | `300` | Signed verification document URL lifetime in seconds. |
| `DRF_THROTTLE_AI_ASSISTANT_MESSAGE_RATE` | `20/hour` | Scoped rate limit for assistant messages and AI search. |

## Production Variables

| Variable | Purpose |
| --- | --- |
| `SECURE_SSL_REDIRECT` | Forces HTTPS in production. Set to `true` after HTTPS is active. |
| `SESSION_COOKIE_SECURE` | Restricts session cookies to HTTPS. Set to `true` after HTTPS is active. |
| `CSRF_COOKIE_SECURE` | Restricts CSRF cookies to HTTPS. Set to `true` after HTTPS is active. |
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
