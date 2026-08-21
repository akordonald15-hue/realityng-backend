# RealityNG System Design Document

Version: 1.0  
Date: 2026-06-16  
Source: RealityNG PRD v1.0  
Audience: Engineering, Product, Design, Operations, Security

## 1. System Overview

RealityNG is an API-first PropTech platform for property discovery, verification, legal review, inspections, artisan services, construction tracking, payment milestone tracking, and admin operations. The first release is a responsive web application. The same backend APIs must support future React Native mobile clients.

Primary system qualities:

1. Trust infrastructure: verification, audit logs, document access control, specialist assignment, and report workflows.
2. Remote execution: diaspora users can request inspections, legal reviews, and construction updates without physical presence.
3. Marketplace liquidity: public property and artisan discovery with moderation and verification gates.
4. Operational control: admins can approve users/listings, assign work, resolve disputes, and monitor risk.
5. Partner readiness: payments and escrow are tracked by RealityNG but external custody is handled by regulated payment or escrow partners.

## 2. Architecture Diagram

```text
Users
  |-- Guest browser
  |-- Tenant / Buyer / Diaspora investor
  |-- Landlord / Agent / Artisan
  |-- Lawyer / Inspector
  |-- Admin / Super Admin
        |
        v
Next.js Web App
  |-- Public marketplace pages
  |-- Authenticated dashboards
  |-- Admin console
  |-- Direct object upload client
        |
        v
Django REST Framework API
  |-- Auth and RBAC
  |-- Marketplace services
  |-- Verification/legal/inspection services
  |-- Artisan and booking services
  |-- Construction and payment milestone services
  |-- Admin operations
        |
        +------------------------+
        |                        |
        v                        v
PostgreSQL + PostGIS        Redis
  |-- Relational data        |-- Cache
  |-- Geo queries            |-- Rate limits
  |-- Audit logs             |-- Celery broker/result backend
  |-- Payment events         |-- Session/OTP state where needed
        |
        v
Celery Workers
  |-- Email notifications
  |-- File processing
  |-- Webhook retries
  |-- Saved search alerts
  |-- SLA reminders
  |-- Report release jobs
        |
        +-------------+-------------+-----------------+---------------+
        |             |             |                 |               |
        v             v             v                 v               v
Object Storage     Email/SMS     Maps/Geocoding    Payments       Observability
S3/Cloudinary      SES/etc.      Google/Mapbox     Paystack/etc.  Sentry/logs/APM
MinIO local
```

## 3. Frontend Architecture

Stack: Next.js, TypeScript, Tailwind CSS.

Application layers:

1. App routes: public pages, auth pages, dashboards, admin console.
2. Feature modules: properties, applications, verifications, legal reviews, inspections, artisans, construction, payments, disputes, notifications.
3. UI system: buttons, forms, filters, tables, tabs, dialogs, upload controls, map components, status badges, timeline, activity feed.
4. API client: typed REST client with request interceptors, auth handling, pagination helpers, and error normalization.
5. State management:
   - Server data: TanStack Query or equivalent for caching, invalidation, retries, pagination, and optimistic UI where safe.
   - Local UI state: React state and URL search params for filters.
   - Auth state: session bootstrap endpoint and cookie/JWT handling.
6. Form management: schema-based validation using Zod or similar aligned with backend serializer rules.
7. Access control: route guards and component-level permission checks based on roles, ownership, assignment, and verification status.

Frontend route groups:

1. Public: home, browse, property detail, artisan directory, artisan detail.
2. Auth: sign up, sign in, verify email/phone, forgot password, role setup.
3. User dashboards: tenant, buyer, landlord, agent, artisan, lawyer, inspector.
4. Operational workflows: applications, viewings, legal reviews, inspections, construction projects, payment milestones, disputes.
5. Admin: queues, approvals, assignments, audit logs, reports, settings.

Frontend rules:

1. All MVP workflows must be mobile responsive.
2. Search filters must be reflected in URL params for shareability.
3. Sensitive documents must never expose direct permanent storage URLs.
4. Trust statuses must distinguish "verified", "under review", "rejected", and "not verified".
5. Error states must give the next action: retry, upload missing document, contact support, or return to dashboard.

## 4. Backend Architecture

Stack: Django, Django REST Framework, Celery.

Recommended Django apps:

1. `accounts`: users, roles, profiles, authentication, KYC references.
2. `properties`: property listings, media, documents, favorites, saved searches, comparisons.
3. `leads`: viewings, rental applications, inquiry records.
4. `artisans`: artisan profiles, service bookings, reviews.
5. `trust`: verification requests, legal reviews, inspection requests, inspection reports.
6. `construction`: projects, milestones, site updates.
7. `payments`: payment milestones, payment events, webhook events, provider references.
8. `documents`: upload intents, document metadata, file access policies.
9. `messaging`: message threads, messages, notifications.
10. `disputes`: dispute cases and evidence.
11. `audit`: audit log and activity feed.
12. `admin_ops`: assignment queues, moderation, operational dashboards.

Service design:

1. Serializers validate request and response shape.
2. ViewSets expose REST resources.
3. Domain services own workflow transitions and side effects.
4. Permissions enforce object-level access.
5. Signals should be limited; prefer explicit service calls for auditable workflows.
6. Celery tasks handle non-transactional side effects after database commit.

Workflow pattern:

```text
API request -> serializer validation -> permission check -> domain service
-> database transaction -> audit log -> enqueue notification/background jobs
-> response
```

## 5. Database Architecture

Database: PostgreSQL with optional PostGIS.

Core design choices:

1. UUID primary keys for externally exposed resources.
2. `created_at`, `updated_at`, and optional `deleted_at` on mutable business entities.
3. Status fields implemented as constrained enums at application level and database check constraints where practical.
4. JSONB used for flexible filters, checklists, provider payloads, and before/after audit snapshots.
5. PostGIS geography point for property coordinates and geo search.
6. Append-only records for audit logs, payment events, webhook events, and legal opinion versions.
7. Soft delete for user-facing content that must preserve auditability.

Read optimization:

1. Index public listing filters: category, status, state, city, lga, price, bedrooms, verification status, published_at.
2. Add GIST index for location point.
3. Add partial indexes for active public listings.
4. Add queue indexes for admin workflows by status, assignee, priority, and created_at.
5. Add unique constraints for favorites and user role assignments.

## 6. Authentication and Authorization

Authentication methods:

1. Web: secure HttpOnly, Secure, SameSite cookies with session or token-backed auth.
2. Mobile later: short-lived JWT access token and rotated refresh token.
3. Email verification required for account activation.
4. Phone OTP required for high-risk workflows.
5. MFA required for admins and recommended for specialists.

Session/JWT rules:

1. Access tokens expire quickly.
2. Refresh tokens rotate on use.
3. Token reuse detection revokes token family.
4. Suspended users are denied immediately.
5. Admin session timeout is shorter than public user timeout.

Authorization model:

1. Role-based: tenant, buyer, landlord, agent, artisan, lawyer, inspector, admin, super admin.
2. Object-based: owner, requester, assignee, reviewer, participant, admin.
3. State-based: draft, submitted, assigned, approved, rejected, suspended, closed.
4. Verification-based: some actions require verified email, phone, identity, or professional status.

Permission examples:

1. Property edit: owner, assigned agent, admin.
2. Legal review document read: requester, assigned lawyer, admin.
3. Inspection report edit: assigned inspector until submission; admin after QA request.
4. Payment milestone approval: admin or authorized project owner depending on milestone policy.
5. Audit log read: admin and super admin only.

## 7. Role-Based Access Control

Role hierarchy:

```text
Super Admin
  -> Admin
      -> Operational specialist roles by assignment
Regular user roles:
  -> Tenant
  -> Buyer
  -> Landlord
  -> Agent
  -> Artisan
  -> Lawyer
  -> Inspector
```

Users may hold multiple non-admin roles. Admin roles require invitation and MFA. Professional roles require approval before public visibility or assignment.

Permission matrix:

| Capability | Guest | User | Landlord/Agent | Artisan | Lawyer | Inspector | Admin | Super Admin |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Browse public listings | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Favorite/save searches | No | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Create property listing | No | No | Yes | No | No | No | Yes | Yes |
| Submit application | No | Yes | No | No | No | No | Yes | Yes |
| Manage artisan profile | No | No | No | Own | No | No | Yes | Yes |
| Issue legal opinion | No | No | No | No | Assigned | No | Yes | Yes |
| Submit inspection report | No | No | No | No | No | Assigned | Yes | Yes |
| Approve listings/users | No | No | No | No | No | No | Yes | Yes |
| Manage admin roles | No | No | No | No | No | No | No | Yes |

## 8. File Upload and Storage Design

Storage options:

1. Production: AWS S3 or Cloudinary.
2. Local/dev: MinIO with S3-compatible API.

Upload flow:

```text
Client -> POST /api/v1/documents/upload-intents/
API -> validates entity permission and file metadata
API -> creates Document(status=upload_pending)
API -> returns signed upload URL and document id
Client -> uploads file directly to object storage
Client -> POST /api/v1/documents/{id}/complete/
API -> marks upload_received and queues scan/processing task
Celery -> scans/transcodes/extracts metadata
API -> marks available or rejected
```

Document access:

1. Public property media can be served through CDN.
2. Sensitive documents are private and read through short-lived signed URLs.
3. Legal, verification, inspection, payment proof, and dispute documents require object-level permission checks.
4. Direct permanent storage URLs must not be stored in client-visible payloads.

Validation:

1. Enforce file type allowlist by document type.
2. Enforce size limits.
3. Calculate checksum.
4. Scan for malware where provider/tooling supports it.
5. Strip or control metadata exposure for public media.

## 9. Notification Design

Channels:

1. MVP: in-app and email.
2. Phase 2: SMS and WhatsApp for urgent operational messages.
3. Future: mobile push notifications.

Notification events:

1. Account verification and password reset.
2. Listing approval, rejection, suspension.
3. Viewing request, acceptance, reschedule, completion.
4. Application submission and decision.
5. Verification status changes.
6. Legal review assignment, document request, opinion issued.
7. Inspection assignment, schedule, report released.
8. Service booking status changes.
9. Construction milestone status changes.
10. Payment milestone proof uploaded, approved, rejected, disputed.
11. Dispute opened, updated, resolved.

Implementation:

1. Create `Notification` row inside transaction for critical events.
2. Queue email/SMS delivery after commit.
3. Store provider message id and delivery status.
4. Use idempotency keys to avoid duplicate sends.
5. User preferences apply to marketing and non-critical updates only.

## 10. Payment Milestone Tracking

RealityNG tracks payment status and supporting evidence. It does not hold funds directly in MVP.

Payment milestone fields:

1. Related entity: property transaction, service booking, legal review, inspection request, construction milestone.
2. Payer and payee.
3. Amount and currency.
4. Due date.
5. Status.
6. External provider and reference.
7. Proof document.
8. Approval/rejection metadata.

Status flow:

```text
pending -> invoiced -> paid_externally -> proof_uploaded -> under_review
-> approved | rejected | disputed | cancelled
```

Rules:

1. Approval to release is separate from actual release.
2. Proof upload must create a payment event.
3. Payment event records are append-only.
4. Disputes lock the affected milestone.
5. UI must clearly state when payment is external or partner-held.

## 11. Escrow Partner-Ready Architecture

Escrow integration should be optional and provider-abstracted.

Provider abstraction:

1. `EscrowProviderClient`: create escrow case, create invoice/payment intent, request release, cancel, refund, fetch status.
2. `PaymentEvent`: normalized event ledger.
3. `WebhookEvent`: raw provider payload, signature status, processing status.
4. `external_reference`: provider case, payment, or release identifier.

Webhook flow:

```text
Provider -> POST /api/v1/webhooks/{provider}/
API -> verifies signature
API -> stores WebhookEvent(raw_payload)
Celery -> processes idempotently
Celery -> appends PaymentEvent
Celery -> updates PaymentMilestone status if transition is valid
Celery -> notifies stakeholders
```

Escrow readiness requirements:

1. No provider-specific fields should leak into core domain tables except provider name and external reference.
2. Webhooks must be idempotent.
3. Release requests require explicit approval workflow.
4. Partner failure should not corrupt internal milestone history.

## 12. Admin Operations Design

Admin console modules:

1. User approvals: agents, artisans, lawyers, inspectors, landlords.
2. Listing approvals: submitted, flagged, expired, duplicated, suspended.
3. Verification queue: intake, assignment, decision, expiry, revocation.
4. Legal review queue: assignment, SLA, document completeness, opinion QA.
5. Inspection queue: assignment, schedule, report QA, release.
6. Payment milestones: proof review, status correction, dispute lock.
7. Disputes: triage, evidence collection, decision, escalation.
8. Audit logs: actor/action/entity filtering.
9. Monitoring: failed jobs, webhook failures, provider health, SLA breach list.

Assignment model:

1. Admin assigns work to approved lawyers/inspectors/reviewers.
2. Assignees see only assigned tasks.
3. Reassignment requires reason.
4. SLA timers begin at assignment or submission based on workflow type.

## 13. Background Jobs with Celery

Celery responsibilities:

1. Send transactional emails.
2. Process uploads and generate thumbnails.
3. Scan documents.
4. Retry failed webhooks.
5. Send saved search alerts.
6. Send SLA reminders.
7. Expire verification badges.
8. Refresh map/geocoding metadata.
9. Recompute listing risk signals.
10. Aggregate dashboard metrics.

Task rules:

1. Tasks must be idempotent.
2. Use retry policies with exponential backoff for provider calls.
3. Use database locks or unique idempotency keys for status-changing tasks.
4. Do not send external notifications until transaction commit.

## 14. Redis Usage

Redis should be used for:

1. Celery broker and optional result backend.
2. API caching for public listing filters, metadata, and dashboard counts.
3. Rate limiting: login, OTP, uploads, contact attempts, webhook endpoints.
4. Short-lived OTP state if not persisted in PostgreSQL.
5. Distributed locks for scheduled tasks and webhook processing.

Redis should not be the source of truth for business workflows.

## 15. Map and Location Service Design

Provider options: Google Maps or Mapbox.

Capabilities:

1. Address autocomplete where provider coverage is acceptable.
2. Geocoding for listing locations.
3. Reverse geocoding for inspector evidence.
4. Map pins and bounds-based listing search.
5. Optional Street View if provider supports the area.

Privacy rules:

1. Exact coordinates may be hidden for public users.
2. Approximate map display should be available for sensitive listings.
3. Exact address can be revealed based on booking, authorization, or admin policy.

Database:

1. Store normalized state, LGA, city, neighborhood.
2. Store `location_point` using PostGIS.
3. Store geocoding confidence and provider metadata.

## 16. Audit Logging Design

Audit events:

1. Login and admin login events.
2. Role changes.
3. Listing approval/rejection/suspension.
4. Verification decisions.
5. Legal review opinion issuance.
6. Inspection report submission and release.
7. Payment milestone changes.
8. Dispute status changes.
9. Sensitive document access.
10. Admin assignment and reassignment.

Audit fields:

1. Actor.
2. Action.
3. Entity type and ID.
4. Before and after JSON.
5. IP address.
6. User agent.
7. Request ID/correlation ID.
8. Timestamp.

Rules:

1. Audit logs are append-only.
2. Logs are not soft deleted.
3. Super admin export requires MFA.
4. Sensitive values should be redacted in snapshots.

## 17. Security Architecture

Controls:

1. TLS for all traffic.
2. Secure cookies for web auth.
3. JWT rotation for mobile.
4. MFA for admins.
5. Object-level permissions for every private resource.
6. Private storage buckets and signed URLs.
7. Rate limiting on auth, OTP, upload, inquiry, and webhook endpoints.
8. CSRF protection for cookie-authenticated unsafe methods.
9. CORS allowlist for web domains.
10. Secrets stored in managed secret storage or environment with restricted access.
11. Dependency scanning and container scanning in CI.
12. Structured security logs.

Fraud controls:

1. Duplicate listing detection.
2. Suspicious price flagging.
3. Duplicate media checksum matching.
4. Contact masking before inquiry.
5. User report flow.
6. Manual review queues.
7. Account restriction and suspension.

## 18. Deployment Architecture

Recommended environments:

1. Local: Docker Compose with Next.js, Django, PostgreSQL, Redis, MinIO.
2. Staging: production-like infrastructure with test providers.
3. Production: managed database, object storage, cache, app services, workers.

Runtime components:

1. Web app service.
2. API service.
3. Celery worker service.
4. Celery beat/scheduler service.
5. PostgreSQL.
6. Redis.
7. Object storage.
8. Reverse proxy/CDN.

Deployment rules:

1. Zero-downtime deploys where possible.
2. Migrations run as release step with rollback planning.
3. Static assets are versioned.
4. Environment variables are validated at startup.
5. Production secrets are not available to preview deployments.

## 19. Monitoring and Observability

Required telemetry:

1. API latency, error rate, throughput.
2. Web vitals.
3. Celery queue depth and task failures.
4. Database slow queries and connection pool usage.
5. Redis memory and latency.
6. Payment webhook failures.
7. Email delivery failures.
8. Storage upload failures.
9. Admin workflow SLA breaches.
10. Security events and rate-limit triggers.

Tools:

1. Sentry for application exceptions.
2. OpenTelemetry-compatible tracing.
3. Centralized structured logs.
4. Uptime monitoring.
5. Provider health dashboard.

## 20. Scaling Plan

Phase 1:

1. Single web service, API service, worker pool.
2. Managed PostgreSQL and Redis.
3. CDN-backed media.
4. PostgreSQL indexed search.

Phase 2:

1. Separate read-heavy public marketplace APIs.
2. Add read replicas if needed.
3. Add dedicated search engine if PostgreSQL search becomes limiting.
4. Scale Celery queues by workload: notifications, uploads, payments, reports.

Phase 3:

1. Service boundaries for marketplace, trust operations, payments, and messaging if team scale requires.
2. Event stream for analytics and partner integrations.
3. Multi-region CDN and disaster recovery improvements.

## 21. Failure Handling

Provider failure:

1. Queue retryable provider operations.
2. Mark external status as pending confirmation.
3. Show user-friendly degraded-state messages.
4. Alert operators when failure thresholds are crossed.

Payment webhook failure:

1. Store raw webhook before processing.
2. Retry idempotently.
3. Provide admin replay action.
4. Never delete failed webhook payloads.

Upload failure:

1. Keep document in `upload_pending` or `processing_failed`.
2. Allow user retry.
3. Clean abandoned uploads with scheduled job.

Database failure:

1. Fail closed on write workflows.
2. Serve cached public data only where safe.
3. Alert immediately.

Workflow failure:

1. Invalid status transitions are rejected.
2. Partial side effects are avoided with transactions.
3. Manual admin correction appends audit records.

## 22. Backup and Recovery Strategy

Database:

1. Daily full backups.
2. Point-in-time recovery.
3. Backup retention policy by environment.
4. Quarterly restore drills.

Object storage:

1. Versioning for sensitive buckets.
2. Lifecycle policies for temporary uploads.
3. Replication or backup for production documents.

Redis:

1. Not authoritative for business records.
2. Restore is optional for cache, required only if queue durability configuration needs it.

Recovery objectives:

1. MVP RPO target: 24 hours initially, improve to 1 hour for production maturity.
2. MVP RTO target: 8 hours initially, improve to 2 hours for production maturity.
3. Critical audit/payment/document data should have stricter operational handling.

