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

No approved Sprint 10 objective was found in the current repository documentation during the freeze audit.

Before implementation begins, leadership/product should confirm:

- Sprint 10 objective
- Included user roles
- Backend scope
- Frontend scope
- Required migrations
- Required third-party services
- Out-of-scope items
- Acceptance criteria
- Deployment expectations

## Architectural Considerations

Sprint 10 planning should account for the Version 2.0 platform shape:

- Property marketplace and services marketplace now coexist.
- Verification and provider approval are separate concepts.
- AI assistant runs in demo mode unless provider credentials are approved.
- Google Maps production activation is deferred.
- Caretekk shares the same production VPS.
- Production is not suitable for heavy testing.
- Services marketplace workflows have many lifecycle states and must not be bypassed from frontend-only logic.

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

## Suggested Sprint 10 Planning Checklist

Before development:

- Write Sprint 10 product brief.
- Confirm backend API contract.
- Confirm frontend route changes.
- Confirm database migration plan.
- Confirm permissions matrix changes.
- Confirm mock-mode requirements.
- Confirm test requirements.
- Confirm rollout and rollback plan.
- Confirm whether production deployment is required at sprint end.

During development:

- Keep scope narrow.
- Add permission tests for every new object relationship.
- Add frontend route and form tests.
- Preserve mock/real separation.
- Update OpenAPI.
- Update release docs.

Before merge:

- Run full backend validation.
- Run full frontend validation.
- Confirm no unrelated rewrites.
- Confirm no infrastructure changes unless approved.

## Sprint 10 Readiness Assessment

RealityNG is technically ready to begin Sprint 10 after leadership confirms the next approved scope.

The only release-governance follow-up that should be resolved before formal version tagging is the existing `v2.0.0` tag conflict.

