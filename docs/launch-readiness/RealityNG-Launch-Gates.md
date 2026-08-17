# RealityNG Launch Gates

Status: planning locked

## Gate A - Software Integrity

Required:

- full backend PostgreSQL regression passes;
- full frontend lint/typecheck/tests/builds pass;
- migrations pass cleanly;
- Redis, Celery, Channels, realtime outbox pass;
- critical persona journeys pass;
- OpenAPI validates with no new errors;
- no unreconciled release artifacts or generated files.

Blocks launch if red.

## Gate B - Security and Private Data

Required:

- IDOR audit complete;
- mass-assignment audit complete;
- role-only authorization mistakes ruled out;
- revoked assignment behavior tested;
- private verification, inspection, construction, payment, and financing documents remain protected;
- signed URLs are authorization-scoped and short-lived;
- upload validation rejects unsafe content;
- JWT/WebSocket security tested;
- financial state transitions and idempotency tested.

Blocks launch if red.

## Gate C - Compliance and Trust

Required:

- privacy policy approved;
- terms and conditions approved;
- escrow and financing disclosures approved;
- user consent and data-sharing language approved;
- data retention/deletion matrix approved;
- moderation, fraud, complaint, and incident policies documented;
- professional review requirements recorded.

Blocks public launch if mandatory approvals are missing.

## Gate D - Infrastructure

Required:

- dedicated production environment ready;
- staging environment available;
- PostgreSQL, Redis, object storage, Celery, Beat, ASGI, and proxy configured;
- backups and restore tested;
- secrets and access control reviewed;
- monitoring and alerting active;
- rollback path proven.

Blocks broad public launch if red.

## Gate E - Performance and Product Readiness

Required:

- staging load/capacity baseline recorded;
- severe N+1 and query issues fixed or accepted;
- no placeholder/fake production content;
- browser/mobile QA completed;
- support and safety flows ready;
- launch-critical empty/error/loading states checked.

Blocks public beta if red.

## Gate F - Beta Go/No-Go

Required:

- Gates A-E green or explicitly accepted by leadership;
- beta cohort defined;
- support and incident owners assigned;
- daily monitoring process defined;
- rollback rehearsal completed;
- go/no-go checklist signed off.

Blocks controlled beta if red.

