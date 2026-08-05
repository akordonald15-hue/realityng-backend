# RealityNG Sprint 9.7 - Testing and Release Hardening Report

## Executive Summary

Sprint 9.7 is a stabilization sprint for the complete Sprint 9.1-9.6 services marketplace. No new business workflow was added. The sprint merged Sprint 9.6 into `main`, validated the combined baseline, hardened suspended-provider restrictions, hardened complaint evidence uploads, documented permissions, and prepared the services marketplace for release review.

The work covers:

- service categories
- provider profiles
- trades and service areas
- portfolio media
- quote requests
- completed service engagements
- booking-linked reviews
- rating aggregates
- provider responses
- review flags
- operational dashboards
- complaints
- warnings
- suspensions
- appeals
- admin moderation

## Sprint 9.6 Mainline Closure

Backend:

- Previous `main`: `dbfc5febeacbc04bba7fcece6456f29291f9a826`
- Sprint 9.6 commit merged: `df398a8bc3a1d69316fd073cfa170872824d56f2`
- Merge method: fast-forward
- Push result: pushed to `origin/main`

Frontend:

- Previous `main`: `664e4782cdae847c1679c9b7f2c02d2d25875800`
- Sprint 9.6 commit merged: `f40fdafeff9cfb1cc5d6d3e67fd55eaf680843b0`
- Merge method: fast-forward
- Push result: pushed to `origin/main`

## Defects Found and Fixed

### Suspended-provider mutation gap

Finding: suspended providers were hidden publicly and could not manage quote status or respond to reviews, but they could still mutate provider-owned setup resources such as profile fields, trades, service areas, and portfolio.

Fix:

- `ProviderProfileMeView.patch` now rejects suspended provider profile edits.
- `ProviderOwnedMixin` now blocks create/update/delete mutations for suspended or archived provider profiles.
- Portfolio cover and reorder actions now also enforce the mutation guard.
- Providers can still read their own records and submit appeals.

Regression test:

- `test_suspended_provider_cannot_mutate_profile_assets`

### Complaint evidence upload validation gap

Finding: complaint evidence accepted a generic file upload without declared MIME, extension, size, or real-content validation.

Fix:

- Added `SERVICE_COMPLAINT_EVIDENCE_MAX_SIZE_MB`.
- Added `SERVICE_COMPLAINT_EVIDENCE_ALLOWED_TYPES`.
- Added `SERVICE_COMPLAINT_EVIDENCE_ALLOWED_EXTENSIONS`.
- `ServiceComplaintEvidenceSerializer` now validates PDF/JPEG/PNG evidence content.
- Complaint evidence responses no longer expose the raw `file` field or a permanent public `file_url`.

Regression test:

- `test_complaint_evidence_upload_is_validated_and_does_not_expose_public_url`

## Functional Regression Summary

Covered by automated backend tests and frontend route/build validation:

- public category browsing
- public provider list/detail
- provider profile setup and moderation
- provider trades and service areas
- portfolio upload and public gallery
- quote request submission and provider/admin management
- completed service booking review eligibility
- customer review submission and edit policy
- public review display and provider response
- review flagging and admin moderation
- customer/provider/admin service dashboards
- complaint creation and admin resolution
- provider warning, suspension, and appeal flows

Manual browser QA remains recommended before public beta because this sprint did not deploy or run browser automation against a live preview.

## Security Findings

Confirmed or hardened:

- public provider querysets exclude non-active and suspended providers
- admin moderation endpoints require admin permissions
- self-review/self-approval controls remain in provider moderation
- complaint ownership is filtered server-side
- provider appeal ownership is filtered server-side
- public serializers exclude private provider address and moderation internals
- hidden/removed/unpublished reviews are excluded from public review APIs
- suspended providers cannot receive public quote requests because they are excluded from public provider lookup
- suspended providers cannot transition quote requests or respond to reviews
- suspended providers now cannot mutate profile assets
- complaint evidence uploads now reject spoofed or unsupported files
- complaint evidence responses no longer serialize permanent file URLs

Deferred security follow-up:

- complaint evidence should move to a dedicated private moderation bucket with short-lived signed admin download URLs when operations needs browser download/preview.
- production MinIO/S3 bucket policy should be verified directly before beta.

## Upload Security

Portfolio images:

- MIME allow-list
- extension allow-list
- size limit
- Pillow real-image validation
- count limit per provider
- owner-only mutation

Verification documents:

- private verification bucket configuration
- MIME and extension allow-list
- size limit
- real PDF/image validation
- signed URL expiry

Complaint evidence:

- MIME allow-list
- extension allow-list
- size limit
- PDF magic-byte validation
- Pillow image validation
- owner/participant/admin object filtering
- permanent file URLs withheld from serializers

## Permission Matrix

Created:

- `docs/RealityNG-Services-Permission-Matrix.md`

The matrix covers anonymous users, customers, providers, suspended providers, property owner/agent roles, and admins across all service endpoint families.

## Query Profiling

Code audit findings:

- public provider list/detail uses `select_related("user", "reviewed_by")` and prefetches trades, service areas, and portfolio categories.
- quote request querysets use `select_related("customer", "provider", "service_category")`.
- review querysets use `select_related("booking__service_category", "customer", "provider")` and prefetch flags.
- complaint querysets use `select_related` for complainant, provider, linked quote/review/booking, assigned admin, and prefetch evidence uploaders.
- appeal querysets use `select_related("provider", "submitted_by", "decided_by")`.
- dashboard serializers use summarized slices and status aggregation rather than unbounded nested result sets.

Indexes already supporting Sprint 9.1-9.6 query paths:

- provider status/type/location/rating/completed job indexes
- trade category hierarchy indexes
- provider trade category/status indexes
- service area location indexes
- portfolio provider/status/display-order indexes
- quote provider/customer/status/location indexes
- booking provider/customer/status/completed indexes
- review provider/customer/status/rating/published indexes
- review flag review/user indexes
- complaint complainant/provider/status/category/assigned-admin indexes
- appeal provider/status/submitted-by/type indexes

No new database index was added in Sprint 9.7 because the hardening fixes did not introduce new query paths.

Limitation: request-level query counts and p95/p99 latency were not measured against a dedicated PostgreSQL staging environment during this local closure. They should be captured in staging before public beta.

## Load Test Result

No uncontrolled load test was run against production or the shared Caretekk VPS. This was intentional.

Recommended beta load-test plan:

- isolated staging stack using PostgreSQL, Redis, MinIO, and the Django backend
- seed at least 1,000 providers, 5,000 quotes, 2,000 reviews, 500 complaints, and 100 appeals
- test 10, 25, and 50 concurrent users
- measure p50, p95, p99 latency and error rate for:
  - `GET /api/v1/services/categories/`
  - `GET /api/v1/services/providers/`
  - `GET /api/v1/services/providers/{slug}/`
  - `POST /api/v1/services/providers/{slug}/quote-requests/`
  - `GET /api/v1/services/dashboard/customer/`
  - `GET /api/v1/services/dashboard/provider/`
  - `GET /api/v1/services/dashboard/admin/`
  - `GET /api/v1/services/admin/providers/`
  - `GET /api/v1/services/admin/reviews/`
  - `GET /api/v1/services/admin/complaints/`
  - `GET /api/v1/services/admin/appeals/`

## Rate-Limit Validation

Scoped throttle configuration exists for:

- service portfolio upload
- quote request creation
- quote request management
- review creation
- review update
- review response
- review flag
- complaint creation
- provider appeal creation

Automated tests cover endpoint correctness; explicit throttle exhaustion tests are recommended in staging because local test settings can make throttle timing brittle.

## State-Machine Audit

Provider profile:

- draft/rejected/more-info can submit
- pending profiles can be approved/rejected/requested for more information
- active profiles can be suspended
- suspended profiles can be reactivated by admin or approved appeal
- suspended/archived profiles cannot mutate owner-managed assets after Sprint 9.7 hardening

Quote request:

- submitted -> viewed -> responded -> closed
- submitted/viewed can become responded
- non-terminal quote can be closed/cancelled
- suspended providers cannot transition quote status

Service booking:

- pending -> confirmed -> completed
- pending/confirmed can be cancelled
- completed bookings require `completed_at`

Review:

- created as pending
- admin can publish/hide/restore/remove/mark disputed
- published reviews can receive one provider response
- suspicious flags can move published reviews to flagged
- only published reviews affect public aggregates

Complaint:

- open -> under review / awaiting customer / awaiting provider / resolved / rejected / escalated / closed
- admin actions are audited

Appeal:

- submitted -> approved/rejected/reopened
- approved suspension appeal reactivates provider

## Migration Audit

Services migrations reviewed:

- `0001_initial.py`
- `0002_seed_trade_categories.py`
- `0003_portfolioimage_servicearea_is_primary_and_more.py`
- `0004_quoterequest.py`
- `0005_servicebooking.py`
- `0006_serviceprovider_average_communication_rating_and_more.py`
- `0007_providerappeal_servicecomplaint_and_more.py`

Clean local SQLite migration applied successfully during Sprint 9.6 post-merge validation. Sprint 9.7 adds no model migration because changes are settings, serializer validation, view guards, tests, and documentation.

PostgreSQL production-schema migration should still be run in staging before deployment because this local closure intentionally did not touch the shared production VPS.

## OpenAPI and Contract Review

OpenAPI generation passed with 0 errors. Existing enum naming warnings remain:

- several `status` choice collisions resolved with generated names
- duplicate naming for `AppealStatusEnum`
- duplicate naming for `PreferredContactMethodEnum`

These are schema polish warnings, not runtime failures. They should be cleaned with additional `ENUM_NAME_OVERRIDES` before generating external SDKs.

## Logging and Observability

Existing audit/event coverage includes:

- service provider created/updated/submitted/approved/rejected/more-info/warned/suspended/reactivated
- trade added/updated/removed
- service area added/updated/removed
- portfolio uploaded/updated/deleted/cover changed/reordered
- quote submitted/viewed/responded/closed/admin closed/admin cancelled
- review created/updated/published/hidden/restored/removed/disputed/provider responded/flagged
- complaint created/evidence uploaded/reviewed/resolved/rejected/escalated/closed/customer requested/provider requested
- provider appeal submitted/approved/rejected/reopened

Sensitive fields such as private addresses, verification documents, moderation notes, fraud metadata, and complaint evidence file paths are not exposed publicly.

## Infrastructure Readiness

This sprint did not deploy. Caretekk and shared VPS services were not restarted or modified.

Release deployment should verify:

- PostgreSQL migration on a staging copy
- Redis availability
- MinIO/S3 bucket policies
- private verification bucket
- complaint evidence storage policy
- Nginx shared-proxy routing
- Cloudflare/SSL health
- RAM, disk, CPU, and swap
- rollback assets and database backup

## Documentation Updates

Updated/created:

- `README.md`
- `docs/environment-variables.md`
- `docs/RealityNG-Services-Permission-Matrix.md`
- `docs/RealityNG-Sprint-9.7-Testing-and-Release-Hardening-Report.md`

## Deferred Issues

- Browser QA across Chrome, Edge, Firefox, and Safari-compatible environments should be completed on a staging or preview deployment.
- Real load testing should be run in an isolated environment rather than against production.
- Complaint evidence download/preview should use a private signed URL flow when operations needs direct file access.
- Existing OpenAPI enum naming warnings should be cleaned before external SDK generation.
- Explicit throttle exhaustion tests should be added in a stable integration-test environment.

## Release Recommendation

Backend release readiness is improved by the Sprint 9.7 hardening fixes. The services marketplace is suitable for PR review and staging validation. Public beta release should wait for browser QA, staging load testing, and infrastructure/bucket-policy verification.
