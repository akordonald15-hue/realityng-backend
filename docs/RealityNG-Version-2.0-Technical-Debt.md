# RealityNG Version 2.0 Technical Debt Register

## Critical

No known critical technical debt is blocking Sprint 10 planning at the time of release freeze.

## High

### Immutable Release Tag Conflict

Current `v2.0.0` tags already exist and point to the earlier verification/assistant release rather than the Sprint 9 production baseline.

Impact:

- The tag name requested for the freeze cannot be reused without rewriting published release history.

Recommendation:

- Do not move the existing tag without explicit leadership approval.
- Prefer a new immutable release tag such as `v2.0.1` or `v2.1.0` for the Sprint 9 production baseline.

### Production Load Testing Not Completed

Heavy load testing was correctly avoided on the shared VPS.

Impact:

- Real p95/p99 capacity for the services marketplace is not yet proven under beta traffic.

Recommendation:

- Run k6, Locust, or Artillery against a staging or temporary VPS.
- Use realistic provider, quote, review, complaint, and dashboard data.

### Google Maps Production Activation Deferred

Google Maps engineering work exists, but production activation is deferred.

Dependencies:

- Google Cloud billing approval
- Restricted browser API key
- Production environment variable
- Coordinate population
- Browser QA

## Medium

### OpenAPI Enum Warnings

OpenAPI validation passes with known enum naming warnings.

Impact:

- Does not block runtime, but may create confusing generated API client types later.

Recommendation:

- Normalize enum component naming before automated client generation becomes part of CI.

### RealityNG MinIO Shared Network Membership

`realityng-minio-1` was observed on `shared-proxy`.

Impact:

- It was pre-existing and not changed during Sprint 9.8, but it should be reviewed because the preferred architecture keeps storage off shared public proxy networks unless explicitly required.

Recommendation:

- Review the reason for MinIO shared-proxy membership in a controlled infrastructure-hardening window.

### Browser QA Coverage

Automated builds and route checks passed, but full manual cross-browser QA should continue before public beta growth.

Recommendation:

- Retest Chrome, Edge, Firefox, and Safari-compatible views on mobile/tablet/desktop.

### Services Data Volume

The provider marketplace needs real approved providers, service areas, portfolios, and review data.

Impact:

- Empty states work, but marketplace value depends on production data onboarding.

Recommendation:

- Prepare an internal provider onboarding and moderation plan before public marketing.

## Low

### Staticfiles Local Warning

Local validation has an unchanged warning about a missing `staticfiles` directory.

Impact:

- Non-blocking for current deployment.

Recommendation:

- Create or document local staticfiles behavior if it continues to distract validation reports.

### Documentation Distribution

Most cross-project operational documentation lives in the backend `docs/` directory.

Impact:

- Frontend engineers must know to check backend docs for release and operations material.

Recommendation:

- Add a short pointer from frontend README to backend release docs if desired.

### Synthetic Smoke Test Cleanup Is Manual

Sprint 9.8 synthetic fixture cleanup was successful, but the process was manual.

Recommendation:

- Create a management command for future production-safe smoke fixture creation and cleanup.

