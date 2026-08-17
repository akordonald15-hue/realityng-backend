# RealityNG Launch Blocker Policy

Status: planning locked

## Launch Blocker

Any of the following blocks public beta or launch unless leadership explicitly accepts the risk in writing:

- critical/high exploitable authorization vulnerability;
- IDOR exposing another user's private data;
- private verification, inspection, construction, payment, complaint, or financing document leakage;
- broken authentication or session handling;
- uncontrolled admin privilege or admin route exposure;
- financial state corruption;
- duplicate or unsafe escrow release/refund behavior;
- invalid financing offer acceptance or self-confirmed funding;
- failed migrations;
- inability to restore a database backup;
- broken core property discovery/inquiry journey;
- production instability;
- missing mandatory legal/compliance approval;
- user-facing wording that misrepresents RealityNG as lender/custodian/underwriter;
- unacceptable tested capacity for the approved beta cohort.

## High Priority Follow-Up

High-priority work may proceed in parallel with beta preparation only if it does not expose users to material harm. Examples:

- OpenAPI enum cleanup;
- improved dashboard performance after acceptable baseline;
- expanded browser coverage beyond the launch support matrix;
- improved admin reporting;
- better content management process.

## Post-Launch Improvement

These should not delay controlled beta unless they become directly tied to a launch blocker:

- advanced analytics;
- live lender API integrations;
- automated credit scoring;
- repayment collection;
- HLS/video transcoding;
- AI recommendations;
- sponsored placements;
- advanced map clustering beyond current baseline;
- expanded notification channels;
- large-scale marketing automation.

## Triage Rule

Every newly discovered item must be classified as one of:

- launch blocker;
- high-priority follow-up;
- post-launch backlog;
- leadership decision.

Unclassified work does not enter Sprints 15-20.

