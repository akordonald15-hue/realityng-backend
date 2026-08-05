# RealityNG Version 2.0 Known Issues and Production Follow-Ups

## Production Follow-Ups

### Google Maps Production Activation

Status:

```text
Deferred
```

Reason:

- Awaiting Google Cloud billing approval and production Maps credentials.

Required actions:

- Enable billing.
- Create a restricted browser API key.
- Add `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`.
- Populate production coordinates.
- Run browser QA.
- Deploy activation configuration.

### Future Load Testing

Status:

```text
Required before larger public beta
```

Production constraint:

- Do not run heavy load tests on the shared RealityNG/Caretekk VPS.

Recommended environment:

- Temporary VPS
- Dedicated staging server
- Local Docker stack

### Release Tag Governance

Status:

```text
Needs leadership decision
```

Issue:

- `v2.0.0` already exists and points to the earlier verification/assistant release.

Recommendation:

- Preserve old immutable tag.
- Use a new tag for the Sprint 9 production baseline, such as `v2.0.1` or `v2.1.0`.

### MinIO Network Review

Status:

```text
Infrastructure hardening follow-up
```

Observation:

- `realityng-minio-1` was observed on `shared-proxy` during Sprint 9.8.
- This was pre-existing and not changed during deployment.

Recommendation:

- Review whether RealityNG MinIO needs shared-proxy access.
- Keep PostgreSQL and Redis private.

### Monitoring Improvements

Status:

```text
Recommended
```

Recommended additions:

- Sentry release markers
- Error alerting
- Disk usage alerts
- Container restart alerts
- PostgreSQL connection monitoring
- Redis memory/eviction monitoring
- MinIO storage growth monitoring
- Cloudflare error-rate monitoring

## Product Follow-Ups

### Provider Data Onboarding

The services marketplace is functional, but public value depends on approved provider inventory.

Recommended actions:

- Seed real provider categories and approved providers.
- Collect portfolio images.
- Review provider profiles.
- Verify providers where applicable.

### Browser QA

Continue manual browser QA before scaling traffic.

Minimum matrix:

- Chrome
- Edge
- Firefox
- Safari-compatible device or substitute
- Mobile widths from 320px to 430px
- Tablet widths from 768px to 1024px
- Desktop widths from 1366px to 1440px

### Admin Operations Runbook

Admin features exist for verification, provider moderation, reviews, complaints, warnings, suspensions, and appeals.

Recommended action:

- Train admins on moderation states and audit expectations.
- Define response SLAs for provider review and complaint queues.

## Non-Issues at Freeze

These items are intentionally not defects:

- Anthropic production credentials are not required while `AI_PROVIDER_MODE=demo`.
- Google Maps fallback is expected until Maps production activation is approved.
- Full booking/payment workflows are out of scope for Version 2.0.
- Notifications delivery is out of scope; event foundations exist for future sprints.

