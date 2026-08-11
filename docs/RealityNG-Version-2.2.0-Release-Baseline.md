# RealityNG Version 2.2.0 Release Baseline

Date: 2026-08-11

## Purpose

Version `v2.2.0` marks the stable production baseline after Sprint 10.

This milestone captures:

- Sprint 9 services marketplace baseline.
- Sprint 10 inspection request workflow.
- Moderated walkthrough video system.
- Inspector assignment foundation.
- Inspection report and evidence workflow.
- Buyer inspection timeline and dashboard surfaces.
- Production deployment and smoke-test completion.

No Sprint 11 implementation is included in this release baseline.

## Release Tag Decision

`v2.1.0` represents the Sprint 9 services marketplace release line.

`v2.2.0` is appropriate for the Sprint 10 milestone because Sprint 10 adds a new major product capability: property inspections and walkthroughs. This is larger than a patch release and should be tracked as a minor version increment.

## Repository Baseline

Backend:

- Repository: `akordonald15-hue/realityng-backend`
- Baseline branch: `main`
- Tag: `v2.2.0`

Frontend:

- Repository: `akordonald15-hue/realityng-frontend`
- Baseline branch: `main`
- Tag: `v2.2.0`

## Production Baseline

Production endpoints:

- Frontend: `https://www.realityng.com`
- Backend API: `https://api.realityng.com/api/v1`
- Health: `https://api.realityng.com/api/v1/health/`

Sprint 10 production validation confirmed:

- RealityNG API health returned `200`.
- Caretekk health returned `200`.
- Nginx validation passed.
- RealityNG backend, PostgreSQL, Redis, and MinIO were healthy.
- Production inspection smoke test passed.

## Deferred Walkthrough Permission Prerequisite

Sprint 10 intentionally keeps walkthrough upload permissions conservative.

Current upload policy:

- Admins may upload and moderate walkthroughs.
- Actual property owners may upload walkthroughs if they hold an approved landlord or agent role.

Deferred policy:

- Assigned agents may upload for assigned properties.
- Verified property managers may upload for managed properties.

This broader policy is not enabled yet because the current property model does not store explicit assigned-agent or property-manager relationships.

Before broadening walkthrough permissions, Sprint 11 or a prerequisite task must add:

- A property assignment or managed-property relationship model.
- Relationship statuses such as active, pending, suspended, revoked, and expired.
- Object-level checks that prove the user is connected to the specific property.
- Admin management surfaces or APIs for creating and revoking assignments.
- Audit logging for assignment lifecycle changes.
- Tests for owner, assigned agent, verified property manager, admin, unrelated professional, buyer, renter, and anonymous access.

Do not grant walkthrough upload access based only on a user's role.

## Sprint 11 Readiness

Sprint 11 can be scoped from this stable baseline.

Recommended Sprint 11 planning assumptions:

- Preserve Sprint 10 inspection and walkthrough behavior.
- Treat property-assignment relationships as a prerequisite if Sprint 11 needs broader agent or property-manager permissions.
- Do not expand video permissions until object-level property relationship checks exist.
- Continue using private storage and signed URLs for sensitive inspection documents.
- Keep walkthrough media moderated before public display.

## References

- `docs/RealityNG-Sprint-10-Integration-and-Deployment-Report.md`
- `docs/RealityNG-Walkthrough-Video-Policy.md`
- `docs/RealityNG-Inspection-Permission-Matrix.md`
- `docs/RealityNG-Inspection-Storage-and-Media-Guide.md`

## Verdict

RealityNG is ready to scope Sprint 11 from the `v2.2.0` stable production baseline.
