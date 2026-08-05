# RealityNG Staging Load Test Plan

## Purpose

This plan defines how to load test the RealityNG Services Marketplace safely without stressing the shared production VPS used by both RealityNG and Caretekk.

Do not run heavy load tests against production.

## Approved Test Environments

Use one of:

- Temporary VPS with Docker Compose
- Dedicated staging server
- Local Docker stack with PostgreSQL, Redis, and MinIO
- CI environment provisioned for performance testing

Do not use:

- Production RealityNG and Caretekk shared VPS
- Production PostgreSQL
- Production Redis
- Production MinIO
- Production Nginx

## Tools

Recommended tools:

- k6
- Locust
- Artillery

Use one tool per run and store scripts in a staging or test directory, not in production deployment folders.

## Test Data

Seed realistic beta data:

- 50 service categories
- 500 approved providers
- 100 suspended or inactive providers
- 2,000 quote requests
- 1,000 bookings
- 1,000 published reviews
- 200 hidden or flagged reviews
- 500 complaints
- 100 appeals
- Portfolio images represented by safe test objects

Do not use real customer documents, real identity records, or real complaint evidence.

## Endpoint Coverage

Public:

- `GET /api/v1/services/categories/`
- `GET /api/v1/services/providers/`
- `GET /api/v1/services/providers/{slug}/`
- `GET /api/v1/services/providers/{slug}/reviews/`
- `POST /api/v1/services/providers/{slug}/quote-requests/`

Customer:

- `GET /api/v1/services/dashboard/customer/`
- `GET /api/v1/services/quote-requests/my/`
- `GET /api/v1/services/reviews/my/`
- `POST /api/v1/services/complaints/`

Provider:

- `GET /api/v1/services/dashboard/provider/`
- `GET /api/v1/services/provider-profile/me/`
- `GET /api/v1/services/provider-profile/portfolio/`
- `GET /api/v1/services/provider-profile/quote-requests/`
- `GET /api/v1/services/provider-profile/reviews/`
- `GET /api/v1/services/provider-profile/complaints/`

Admin:

- `GET /api/v1/services/dashboard/admin/`
- `GET /api/v1/services/admin/providers/`
- `GET /api/v1/services/admin/quote-requests/`
- `GET /api/v1/services/admin/reviews/`
- `GET /api/v1/services/admin/complaints/`
- `GET /api/v1/services/admin/appeals/`

## Load Profiles

### Smoke Load

- Users: 1 to 2
- Rate: 1 to 2 requests per second
- Duration: 30 to 60 seconds
- Purpose: deployment smoke only
- Allowed against production: yes, only during controlled release validation

### Beta Baseline

- Users: 5 to 10
- Duration: 5 minutes
- Purpose: staging baseline
- Allowed against production: no

### Beta Peak

- Users: 25 to 50
- Duration: 10 minutes
- Purpose: staging peak behavior
- Allowed against production: no

### Soak Test

- Users: 10 to 25
- Duration: 30 to 60 minutes
- Purpose: detect memory, connection, and storage issues
- Allowed against production: no

## Metrics

Capture:

- Requests per second
- p50 latency
- p95 latency
- p99 latency
- Error rate
- CPU usage
- RAM usage
- Swap usage
- Disk usage
- PostgreSQL connections
- Slow queries
- Redis memory
- Redis evictions
- MinIO response errors
- Backend worker restarts
- Nginx 4xx and 5xx counts

## Acceptance Targets for Beta

Initial targets:

- Public list endpoints p95 under 800 ms in staging
- Provider detail p95 under 1000 ms in staging
- Dashboard endpoints p95 under 1200 ms in staging
- Error rate under 1 percent
- No backend crash loops
- No database connection exhaustion
- No Redis eviction under expected beta load
- No private object access leakage

Targets should be revised after real beta traffic is observed.

## Abort Criteria

Stop testing immediately if:

- Error rate exceeds 5 percent for more than 60 seconds
- Backend containers restart repeatedly
- PostgreSQL connections are exhausted
- RAM or swap usage becomes unsafe
- MinIO returns repeated storage errors
- Any test accidentally points at production

## Reporting Template

Record:

- Environment
- Code commits tested
- Dataset size
- Tool used
- Script path
- Load profile
- Metrics summary
- Error summary
- Database observations
- Redis observations
- Storage observations
- Recommended fixes

