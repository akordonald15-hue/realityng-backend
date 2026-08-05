# RealityNG Sprint 10 Prerequisites

## Purpose

This document defines the prerequisites for starting Sprint 10 after the RealityNG Version 2.0 release freeze.

Sprint 10 should not begin until the release baseline is acknowledged and the next sprint scope is confirmed by leadership.

## Required Baseline

Before branching for Sprint 10:

- Backend `main` must match `origin/main`.
- Frontend `main` must match `origin/main`.
- Working trees must be clean.
- Sprint 9 feature branches must remain intact.
- Production must remain healthy.
- Rollback assets must remain available.
- No emergency production incident may be open.

## Branching Rule

Create Sprint 10 branches from latest `origin/main`.

Do not branch from:

- Sprint 9 feature branches
- Local uncommitted work
- Production release directories
- Old integration branches

Recommended branch names:

```text
feature/sprint-10-<approved-scope>
```

Use one backend branch and one frontend branch when both repositories are involved.

## Scope Confirmation Required

Sprint 10 has been defined as the inspection and walkthrough layer.

Before implementation begins, leadership/product should confirm:

- Sprint 10 objective and acceptance criteria
- Included user roles
- Backend scope
- Frontend scope
- Required migrations
- Required third-party services
- Out-of-scope items
- Acceptance criteria
- Deployment expectations

Approved Sprint 10 roadmap:

```text
10.1 - Inspection request workflow
10.2 - Walkthrough video system
10.3 - Inspector assignment
10.4 - Inspection report and evidence
10.5 - Inspection timeline and tracking
10.6 - Buyer dashboard for inspections
10.7 - Release hardening and deployment
```

Walkthrough upload policy:

- Landlords may upload walkthroughs for owned properties.
- Agents may upload walkthroughs for assigned or managed properties.
- Verified property managers may upload walkthroughs for managed properties.
- Admins may upload or moderate walkthroughs for any property.
- Buyers, renters, anonymous users, and unverified property managers may not upload walkthroughs.
- Walkthroughs must pass moderation before becoming public.

## Architectural Considerations

Sprint 10 planning should account for the Version 2.0 platform shape:

- Property marketplace and services marketplace now coexist.
- Verification and provider approval are separate concepts.
- AI assistant runs in demo mode unless provider credentials are approved.
- Google Maps production activation is deferred.
- Caretekk shares the same production VPS.
- Production is not suitable for heavy testing.
- Services marketplace workflows have many lifecycle states and must not be bypassed from frontend-only logic.
- Inspection workflows should be implemented in a dedicated `apps.inspections` backend app unless implementation discovery proves a tighter fit inside `apps.properties`.
- Walkthrough videos must use strict upload validation and moderation.
- Inspection evidence should use private storage and signed access patterns.
- Approved walkthrough media and private inspection evidence must remain separate concepts.
- The definition of `verified property manager` must be explicit before upload permissions are implemented.

## High-Risk Areas to Protect

Future Sprint 10 work must not regress:

- Authentication
- Role authorization
- Property marketplace
- Verification document privacy
- Provider public visibility rules
- Suspended-provider restrictions
- Quote request ownership
- Booking-linked review eligibility
- Complaint evidence privacy
- Admin-only moderation
- Audit events
- Demo assistant mode
- Maps fallback
- Caretekk production stability
- Property ownership and assigned-agent permissions
- Verified property-manager checks
- Walkthrough moderation before public display
- Private inspection evidence access
- Buyer inspection dashboard scoping
- Admin-only inspection moderation

Sprint 10 must not introduce:

- Payments
- Escrow
- Real-time messaging
- Notification delivery
- Video transcoding pipeline
- CDN migration
- Inspector payout workflow
- Legal inspection certification claims not backed by approved policy

## Suggested Sprint 10 Planning Checklist

Before development:

- Write Sprint 10 product brief using the 10.1-10.7 roadmap.
- Confirm backend API contract.
- Confirm frontend route changes.
- Confirm database migration plan.
- Confirm permissions matrix changes.
- Confirm mock-mode requirements.
- Confirm test requirements.
- Confirm rollout and rollback plan.
- Confirm whether production deployment is required at sprint end.
- Confirm walkthrough file-size, MIME type, extension, and storage limits.
- Confirm inspection report fields.
- Confirm inspector eligibility.
- Confirm verified property-manager definition.

During development:

- Keep scope narrow.
- Add permission tests for every new object relationship.
- Add frontend route and form tests.
- Preserve mock/real separation.
- Update OpenAPI.
- Update release docs.
- Keep public walkthrough serialization restricted to approved media only.
- Keep private inspection evidence inaccessible without authorization.

Before merge:

- Run full backend validation.
- Run full frontend validation.
- Confirm no unrelated rewrites.
- Confirm no infrastructure changes unless approved.
- Run upload/security tests.
- Run browser QA for property detail, inspection dashboard, admin moderation, and mobile upload flows.

## Sprint 10 Readiness Assessment

RealityNG is technically ready to begin Sprint 10. The approved roadmap is feasible with the current architecture because the platform already has:

- Role and permission foundations.
- Property ownership and moderation patterns.
- Verification records.
- Private document handling.
- Media-storage integration.
- Admin review workflows.
- Dashboard infrastructure.
- Audit/event conventions.

The highest-risk Sprint 10 area is walkthrough video handling because it can affect storage, bandwidth, moderation workload, and browser performance.

Recommendation:

- Start with 10.1 inspection requests.
- Keep 10.2 walkthrough uploads conservative.
- Defer transcoding, streaming optimization, and CDN-specific video architecture until after the first moderated upload workflow is validated.
