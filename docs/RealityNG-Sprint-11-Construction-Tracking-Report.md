# RealityNG Sprint 11 Construction Tracking Report

## Executive Summary

Sprint 11 introduces construction project tracking from the stable `v2.2.0` baseline.
The implementation adds an explicit property assignment model, a dedicated
`apps.construction` backend domain, private construction evidence storage, project
stakeholders, milestone progress tracking, inspection links, owner/project-manager/admin
dashboards, and audit events.

The sprint intentionally does not implement a full construction ERP, payments, procurement,
contractor billing, scheduling optimization, media transcoding, or Sprint 12 functionality.

## Property Assignment Foundation

`apps.properties.PropertyAssignment` now records explicit property-level authority.

Capabilities are intentionally small:

- `manage_listing`
- `manage_walkthroughs`
- `manage_viewings`
- `manage_inspections`
- `manage_construction`
- `view_private_project_data`

Walkthrough upload authorization now supports:

- property owners with approved landlord or agent role;
- admins;
- active assigned users with `manage_walkthroughs`.

Revoked, suspended, expired, declined, unrelated, or role-only users are denied.

## Backend Domain

New app:

```text
apps.construction
```

Models:

- `ConstructionProject`
- `ProjectStakeholder`
- `ConstructionMilestone`
- `ConstructionProgressUpdate`
- `ConstructionEvidence`
- `ConstructionMilestoneInspection`
- `ConstructionTimelineEvent`

Project progress is calculated from weighted milestone progress. Historical progress
updates are append-only and remain visible in the project timeline.

## APIs

Project routes:

- `GET/POST /api/v1/construction/projects/`
- `GET/PATCH /api/v1/construction/projects/{slug}/`
- `POST /api/v1/construction/projects/{slug}/transition/`
- `GET /api/v1/construction/projects/{slug}/timeline/`

Nested project routes:

- `/api/v1/construction/projects/{slug}/stakeholders/`
- `/api/v1/construction/projects/{slug}/milestones/`
- `/api/v1/construction/projects/{slug}/updates/`
- `/api/v1/construction/projects/{slug}/evidence/`

Dashboard routes:

- `GET /api/v1/construction/dashboard/owner/`
- `GET /api/v1/construction/dashboard/operations/`
- `GET /api/v1/construction/dashboard/admin/`

Inspection integration:

- `POST /api/v1/construction/projects/{slug}/milestones/{id}/request-inspection/`

This creates an existing Sprint 10 `InspectionRequest` and links it to the milestone.

## Storage

Construction evidence uses private object storage by default:

```env
CONSTRUCTION_EVIDENCE_BUCKET=realityng-construction-evidence
CONSTRUCTION_SIGNED_URL_EXPIRY_SECONDS=300
```

No construction evidence exposes permanent public URLs. Signed URLs include
`Cache-Control: no-store, private` on signed-url endpoints.

No synchronous video transcoding, HLS generation, FFmpeg processing, or thumbnail extraction
is performed on the shared VPS.

## Security

Key safeguards:

- role alone never grants property authority;
- project creation requires property ownership, admin access, or explicit assignment;
- stakeholders have project-scoped access, not global roles;
- investors/viewers are read-only by default;
- operational updates require project-manager/operator/owner/admin authority;
- private evidence access is object-level checked;
- milestone completion is blocked by required inspection gates where applicable;
- all sensitive actions emit audit events.

## Frontend Integration

Frontend routes added:

- `/dashboard/construction`
- `/dashboard/construction/operations`
- `/dashboard/construction/projects/[slug]`
- `/admin/construction`

The frontend includes a dedicated construction API client and isolated mock data support.

## Validation

Automated coverage added:

- property-assignment walkthrough permission regression;
- project creation authorization;
- stakeholder read-only access;
- weighted progress update approval;
- inspection-gated milestone completion;
- private construction evidence signed access;
- milestone-to-inspection request integration.

## Known Limitations

- No heavy media processing on the shared VPS.
- Advanced milestone dependency scheduling is deferred.
- Email invitation delivery for stakeholders is not implemented; the backend records invitation state.
- Production object-storage bucket creation must be included in deployment.

## Sprint 12 Boundary

Sprint 11 does not implement payments, procurement, contractor quote workflows,
advanced scheduling, construction budgets, live chat, notification delivery, or AI progress
analysis.

## Readiness

Sprint 11 is ready for validation and PR review once the full backend and frontend suites pass.
