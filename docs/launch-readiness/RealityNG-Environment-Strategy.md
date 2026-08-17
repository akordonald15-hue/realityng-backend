# RealityNG Environment Strategy

Status: planning locked

## Local / Development

Purpose:

- feature development;
- unit and targeted integration tests;
- disposable data;
- local Docker PostgreSQL/Redis/MinIO where practical.

Rules:

- never connect to production PostgreSQL, Redis, or MinIO;
- do not store real customer documents;
- use mock/demo partner credentials only;
- local failures must not be hidden by SQLite fallback when PostgreSQL behavior is under review.

## Staging

Purpose:

- release candidate validation;
- PostgreSQL migrations;
- Redis/Celery/Channels integration;
- browser QA;
- partner sandbox/manual-mode validation;
- load and capacity testing;
- rollback rehearsal.

Required services:

- PostgreSQL;
- Redis;
- MinIO or production-equivalent S3-compatible storage;
- backend ASGI/Daphne;
- Celery worker;
- Celery Beat;
- frontend connected to staging API;
- Cloudflare/DNS-like routing where feasible.

Rules:

- use synthetic or anonymized data;
- no real financing, escrow, or legal customer documents;
- load testing belongs here, not production.

## Production

Purpose:

- real users and controlled beta traffic.

Rules:

- production is not the primary test environment;
- no heavy load tests;
- no destructive data tests;
- migrations only after backup;
- rollback path must exist before deployment;
- all private buckets remain private;
- monitoring and alerting must be active before public beta.

## Data

- PostgreSQL is authoritative for app state.
- Object storage holds media/documents; binaries must not be stored in PostgreSQL.
- Private documents require signed access.
- Backups must include database, environment/configuration, deployment inventory, and storage classification.

## Redis

Use Redis for:

- cache;
- Channels;
- Celery broker/result backend where configured;
- throttling.

Sprint 17 should decide whether these concerns need separate Redis databases or instances.

## Storage Classification

| Asset | Classification |
| --- | --- |
| Public property images | Public or CDN-safe |
| Approved public walkthrough media | Public/controlled public |
| Verification documents | Private signed |
| Inspection evidence/reports | Private signed |
| Construction evidence | Private signed |
| Payment proofs | Private signed |
| Financing documents | Private signed |
| Complaint evidence | Private signed |

## Monitoring

Minimum launch monitoring:

- uptime checks;
- API health;
- frontend health;
- CPU/RAM/disk/swap;
- PostgreSQL connections and slow queries;
- Redis memory/evictions;
- Celery queue health;
- realtime outbox failures;
- WebSocket errors;
- object storage errors;
- financial webhook/partner failures;
- Sentry or equivalent exception tracking.

