# RealityNG Sprint 10 Planning

## Planning Status

Sprint 10 has not started.

Sprint 10 has been defined as the inspection and walkthrough layer for RealityNG's trust-first property marketplace.

This document is a roadmap only. It does not implement Sprint 10.

## Recommended Sprint Objective

Recommended objective:

```text
Introduce inspection requests, moderated walkthrough videos, inspector assignment, inspection reports, evidence, timelines, and buyer-facing inspection tracking.
```

Sprint 10 builds on the Version 2 platform:

- Property marketplace
- Verification layer
- Demo assistant
- Location intelligence foundation
- Services marketplace
- Provider governance
- Reviews and complaints
- Admin moderation

Sprint 10 should improve buyer confidence by allowing inspection workflows to sit naturally between property discovery, viewing, application, and trust verification.

## Business Value

Sprint 10 should help RealityNG:

- Reduce uncertainty for buyers, renters, and diaspora users.
- Make property discovery more visual and trustworthy.
- Create a structured inspection workflow instead of informal offline coordination.
- Give admins operational visibility into inspection status and evidence.
- Allow approved walkthrough media to support property decisions without exposing unmoderated content.
- Prepare the platform for future inspection services, payments, messaging, and stronger verification workflows.

## Approved Sprint 10 Roadmap

### 10.1 - Inspection Request Workflow

Objective:

- Allow buyers/renters to request an inspection or professional property check from a property page or dashboard.

Core scope:

- Inspection request model and lifecycle.
- Request creation from property detail.
- Buyer dashboard inspection request list.
- Landlord/agent/admin visibility where appropriate.
- Statuses such as `requested`, `under_review`, `accepted`, `rejected`, `cancelled`.
- Audit events.
- Permission tests.

Complexity:

```text
Medium
```

Backend impact:

- New `apps.inspections` app is recommended.
- Link requests to `Property`, requesting user, property owner/agent, and optional assigned inspector.
- Reuse existing property object permissions.

Frontend impact:

- Property detail inspection CTA.
- Buyer inspection dashboard surface.
- Admin inspection queue.
- Empty/loading/error states.

### 10.2 - Walkthrough Video System

Objective:

- Allow eligible users to upload walkthrough videos for properties, with moderation before public display.

Upload eligibility:

- Landlords for owned properties.
- Agents for assigned or managed properties.
- Verified property managers for managed properties.
- Admins for any property.

Not allowed:

- Buyers, renters, anonymous users, or unverified property managers.

Moderation rule:

- A walkthrough upload must not become public until approved through moderation.

Recommended lifecycle:

```text
draft
pending_review
approved
rejected
hidden
archived
```

Core scope:

- Walkthrough video model.
- Upload validation.
- File size limits.
- Allowed MIME/extension checks.
- Moderation queue.
- Public display of approved walkthroughs only.
- Admin approve/reject/hide actions.
- Audit events.

Storage approach:

- Use media/object storage.
- Do not store unmoderated videos as public listing media.
- Approved public playback can use public media URLs or signed access depending on storage policy.
- Defer transcoding, streaming optimization, CDN video pipeline, and automatic thumbnails unless already safely supported.

Complexity:

```text
Medium to Large
```

Key risk:

- Video files can grow storage and bandwidth quickly on the lean VPS.
- Keep strict size limits and avoid production stress.

### 10.3 - Inspector Assignment

Objective:

- Allow admins or authorized operators to assign an inspector or inspection-capable provider to an inspection request.

Core scope:

- Inspector eligibility rules.
- Assignment model or fields.
- Assignment status.
- Admin assignment UI.
- Inspector dashboard entry.
- Audit events.
- Notifications foundation events only, no delivery.

Architecture note:

- Inspectors may reuse the existing roles system or services-provider foundation, but assignment permissions must stay separate from service quote/review flows.

Complexity:

```text
Medium
```

### 10.4 - Inspection Report and Evidence

Objective:

- Allow assigned inspectors/admins to submit structured inspection reports and evidence.

Core scope:

- Inspection report model.
- Condition notes.
- Utility observations.
- Safety observations.
- Location/context notes.
- Evidence uploads.
- Private evidence storage.
- Admin review of submitted reports.
- Buyer-safe report summary.

Storage rule:

- Evidence should use private storage and signed access patterns, similar to verification documents and complaint evidence.

Do not expose:

- Raw internal notes.
- Private object keys.
- Unapproved evidence.

Complexity:

```text
Large
```

### 10.5 - Inspection Timeline and Tracking

Objective:

- Give buyers, property owners, inspectors, and admins a chronological record of inspection progress.

Core scope:

- Timeline event model or audit-log projection.
- Events for request creation, review, assignment, upload, report submission, approval, rejection, completion, cancellation.
- Dashboard timeline components.
- Admin timeline view.
- Buyer-facing status tracking.

Architecture note:

- Reuse existing audit/event conventions where possible.
- Avoid building notification delivery in Sprint 10.

Complexity:

```text
Medium
```

### 10.6 - Buyer Dashboard for Inspections

Objective:

- Let buyers/renters track inspection requests, assigned inspectors, report status, walkthrough availability, and final inspection outcomes.

Core scope:

- Buyer inspection dashboard.
- Current inspection status.
- Timeline preview.
- Report summary when approved.
- Walkthrough status/availability.
- Next available action.
- Empty and error states.
- Mobile responsive layout.

Complexity:

```text
Medium
```

### 10.7 - Release Hardening and Deployment

Objective:

- Validate the complete Sprint 10 inspection and walkthrough system before production release.

Core scope:

- Backend validation.
- Frontend validation.
- Upload/security tests.
- Permission matrix update.
- Browser QA.
- Storage growth review.
- Production-safe smoke plan.
- Rollback plan.
- Deployment report.

Complexity:

```text
Medium
```

## Recommended Implementation Order

1. Confirm Sprint 10 acceptance criteria with leadership.
2. Create backend and frontend Sprint 10 branches from latest `origin/main`.
3. Implement 10.1 inspection request workflow first.
4. Implement 10.2 walkthrough video upload and moderation with strict limits.
5. Implement 10.3 inspector assignment.
6. Implement 10.4 inspection reports and private evidence.
7. Implement 10.5 timeline tracking.
8. Implement 10.6 buyer dashboard surfaces.
9. Complete 10.7 release hardening, docs, and deployment plan.

## Architecture Impact

Recommended backend architecture:

- Create a new `apps.inspections` Django app.
- Keep property marketplace concerns in `apps.properties`.
- Keep service-provider marketplace concerns in `apps.services`.
- Link inspections to property records and users without duplicating property ownership logic.
- Reuse audit-log conventions.
- Reuse private storage patterns for inspection reports/evidence.
- Reuse public media patterns cautiously for approved walkthrough videos.

Expected backend impact:

- New inspection request models.
- Walkthrough media model.
- Inspector assignment fields/models.
- Inspection report and evidence models.
- Timeline/event records.
- New permissions and serializers.
- New admin/moderation APIs.

Expected frontend impact:

- Property detail inspection CTA.
- Walkthrough upload/manage screens for eligible roles.
- Admin walkthrough moderation.
- Admin inspection request queue.
- Inspector assignment interface.
- Inspector dashboard or assigned inspections view.
- Buyer inspection dashboard.
- Inspection timeline and report display.

## Database Impact

Sprint 10 will require database migrations.

Likely models:

- `InspectionRequest`
- `PropertyWalkthrough`
- `InspectionAssignment`
- `InspectionReport`
- `InspectionEvidence`
- `InspectionTimelineEvent`

Likely indexes:

- property/status/created_at
- requester/status/created_at
- assigned_inspector/status/created_at
- moderation_status/created_at
- report/status/submitted_at

Migration design should be incremental across Sprint 10 phases rather than one oversized migration.

## Dependencies

- Leadership approval of inspection and walkthrough acceptance criteria
- Clear definition of `verified property manager`
- Storage limits for walkthrough video uploads
- Admin moderation policy for public walkthroughs
- Inspector role/eligibility policy
- Vercel access if frontend production deployment is required
- Admin/operator availability for workflow validation
- Staging environment if upload or performance testing is required

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Video uploads consume storage/bandwidth | Production instability and cost | Strict file limits, staged testing, no heavy production upload tests. |
| Unmoderated walkthrough appears publicly | Trust/privacy issue | Enforce backend moderation before public serialization. |
| Unauthorized user uploads walkthrough | Security issue | Object-level property ownership/management checks and tests. |
| Verified property manager definition is unclear | Permission ambiguity | Define role and verification dependency before 10.2 implementation. |
| Inspector assignment overlaps services marketplace | Confusing user experience | Keep inspection assignment distinct from service quotes/bookings. |
| Private evidence leaks publicly | Severe privacy issue | Use private storage and signed access only. |
| Sprint 10 scope becomes too broad | Delays and regressions | Keep the 10.1-10.7 sequence and defer payments/messaging. |
| Production upload testing stresses shared VPS | Caretekk disruption | Use staging for upload/performance tests; production smoke only. |

## Suggested Sprint 10 Phase Structure

### Phase 1: 10.1 Inspection Request Workflow

- Backend request lifecycle.
- Property detail CTA.
- Buyer dashboard request list.
- Admin queue.

### Phase 2: 10.2 Walkthrough Video System

- Eligible uploader policy.
- Upload validation.
- Moderation before public display.
- Public approved walkthrough display.

### Phase 3: 10.3 Inspector Assignment

- Inspector eligibility.
- Admin assignment.
- Inspector visibility.

### Phase 4: 10.4 Inspection Report and Evidence

- Structured report.
- Private evidence.
- Admin review.
- Buyer-safe summary.

### Phase 5: 10.5 Timeline and Tracking

- Inspection timeline events.
- Buyer/admin/inspector tracking.

### Phase 6: 10.6 Buyer Dashboard

- Buyer-facing inspection center.
- Status, timeline, report, walkthrough availability.

### Phase 7: 10.7 Release Hardening

- Update docs.
- Update rollback notes.
- Confirm production smoke plan.
- Prepare deployment report template.

## Acceptance Criteria Template

Sprint 10 is ready for review when:

- Inspection requests can be created and tracked.
- Walkthrough uploads are limited to landlords, agents, verified property managers, and admins.
- Walkthroughs require moderation before public display.
- Inspectors can be assigned by authorized users.
- Inspection reports and evidence are private until approved for buyer-safe display.
- Buyers can track inspection status from their dashboard.
- No Sprint 9 workflow regresses.
- Tests pass.
- Builds pass.
- OpenAPI is valid.
- Production rollout and rollback plan is documented.
- Caretekk safety constraints are preserved.

## Executive Recommendation

Start Sprint 10 with 10.1 inspection requests and keep walkthrough video uploads scoped and moderated.

Do not begin with video streaming/transcoding complexity. The first video implementation should be conservative: strict upload limits, approved formats only, moderation before public display, and no public exposure of unapproved media.
