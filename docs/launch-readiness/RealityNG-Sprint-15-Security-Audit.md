# RealityNG Sprint 15 Security Audit

Status: engineering audit complete; visual QA remains blocked

## Property Assignment Boundary

| Case | Result |
| --- | --- |
| Active assignment with required capability | PASS |
| Active assignment without required capability | DENIED |
| Revoked/suspended/expired assignment | DENIED |
| Same role without assignment | DENIED |
| Assignment for another property | DENIED |
| Owner | Intended owner access |
| Admin | Intended administrative access |

Capabilities found in current code include `manage_listing`, `manage_leads`,
`manage_walkthroughs`, `manage_construction`, `view_private_project_data`, and
`manage_transactions`. Walkthrough, construction, leads, transaction, and
escrow tests exercise capability-specific access. Inspection assignment status
is a separate explicit boundary and was hardened by S15-AUTH-001.

## Financial Domain

- Buyer, owner, applicant, provider and partner identities are server-derived.
- Private/admin serializer fields are read-only or absent from public inputs.
- Transaction, escrow, release/refund, reconciliation and financing transitions
  are explicit service-layer operations.
- PostgreSQL row locks guard transaction, escrow, condition, release, refund,
  reconciliation, application and offer transitions.
- Conditional uniqueness constraints enforce release/refund idempotency.
- Release and refund conflict in both directions; open disputes gate release.
- Provider funding cannot be self-asserted by a frontend user.
- HMAC signatures use constant-time comparison; invalid signatures fail.
- Webhook event identity and replay are idempotent.
- Financing consent terms are server-controlled and consent creation is
  idempotent.
- Expired offers cannot be accepted; accepting one withdraws competing offers.
- Large monetary values retain Decimal precision.
- Sensitive operations emit audit/timeline events.
- Product copy and architecture preserve RealityNG's orchestration-only role.

## Realtime Security

Automated coverage proves anonymous denial, JWT subprotocol acceptance,
query-string-token rejection, participant admission, nonparticipant denial,
sender identity derivation, empty/oversized rejection, user-scoped throttling,
HTTP/WebSocket idempotency, cursor reconnect, notification isolation, retryable
outbox failure, and recovery delivery. Redis, Celery worker, Beat and ASGI were
also exercised against isolated local services.

## Remaining Controls

- Malware scanning/quarantine is absent and remains a defense-in-depth risk.
- Professional penetration testing remains recommended before broad launch.
- Visual browser/device QA requires an available browser-control session.

