# RealityNG Inspection Architecture

Sprint 10 adds `apps.inspections` as a dedicated backend app for property inspection requests, virtual walkthrough moderation, inspector assignments, private reports, private evidence, and timeline tracking.

## Core Principles

- Inspections complement the existing property marketplace; they do not replace inquiries, viewing requests, applications, or verification.
- Walkthrough videos are public only after moderation.
- Inspection reports and evidence are private and served only through authorized backend flows and signed URLs.
- Exact access details, private notes, and evidence object keys must never be exposed publicly.
- Google Maps production activation remains independent from inspections.

## Main Models

- `InspectionRequest`: customer request linked to a property and requester.
- `InspectorProfile`: operational profile for users approved to perform inspections.
- `InspectionAssignment`: assignment history between inspections and inspectors.
- `PropertyWalkthrough`: moderated public walkthrough videos for property pages.
- `InspectionReport`: inspector-created report linked one-to-one with an inspection request.
- `InspectionEvidence`: private report evidence files.
- `InspectionTimelineEvent`: user-visible and internal status history.

## Lifecycles

Inspection request:

```text
requested -> under_review -> approved -> assigned -> scheduled -> in_progress
-> report_submitted -> report_under_review -> completed
```

Alternative terminal or review states:

```text
needs_more_information
cancelled
rejected
expired
```

Walkthrough:

```text
draft -> pending_review -> approved
draft -> pending_review -> rejected
approved -> hidden
any non-terminal -> archived
```

Report:

```text
draft -> submitted -> under_review -> approved
submitted -> needs_revision -> submitted
submitted -> rejected
```

## API Roots

- `/api/v1/inspections/requests/`
- `/api/v1/inspections/assignments/`
- `/api/v1/inspections/reports/`
- `/api/v1/inspections/evidence/`
- `/api/v1/inspections/walkthroughs/`
- `/api/v1/inspections/admin/requests/`
- `/api/v1/inspections/admin/walkthroughs/`
- `/api/v1/inspections/admin/reports/`
- `/api/v1/inspections/admin/inspectors/`
- `/api/v1/inspections/dashboard/customer/`
- `/api/v1/inspections/dashboard/inspector/`
- `/api/v1/inspections/dashboard/admin/`

## Deferred Dependencies

The current property model supports ownership through `Property.owner`. Assigned agent and verified property-manager upload permissions require a future explicit property-management relationship. Until that relationship exists, non-admin walkthrough upload permission is conservative: approved landlord/agent property owners only.
