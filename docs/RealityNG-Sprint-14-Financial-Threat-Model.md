# RealityNG Financial Threat Model

Status: Planning only  
Scope: Sprint 14 payment proof foundation, Sprint 14.1 escrow, Sprint 14.2 financing.

## Security Objective

RealityNG financial workflows must prevent unauthorized access, false payment claims, duplicate fund movement, forged provider events, private document leakage, and misleading public financial claims.

The backend is the authority. The frontend may guide the user but must never decide authorization, release eligibility, funding status, financing eligibility, or partner trust.

## Assets

- transaction records
- escrow status and release decisions
- payment proofs
- escrow webhook events
- financing applications
- financing documents
- applicant consent
- partner offers
- private signed URLs
- provider API credentials
- audit records
- admin decisions

## Threats And Controls

| Threat | Impact | Controls | Tests |
| --- | --- | --- | --- |
| IDOR on transactions | user sees another user's payment data | object-level permission checks, assignment-aware authorization | cross-user GET/PATCH denial |
| IDOR on signed proof/document URL | private files exposed | signed URL endpoint checks object permission before signing | guessed proof/document id denied |
| Mass assignment of buyer/seller/owner | attacker creates transaction under another user | derive parties server-side from property/application | payload-injected owner ignored |
| Fake payment proof | false payment confidence | proof status remains pending until admin/provider verification | public serializers distinguish unverified proof |
| Forged escrow webhook | false funding/release | provider signature validation, event idempotency | invalid signature rejected |
| Webhook replay | duplicate funding/release | unique provider event id, idempotent state transition | repeated webhook has one effect |
| Duplicate release instruction | double payment | release idempotency key, state locking | concurrent release produces one instruction |
| Amount/currency tampering | financial mismatch | server-side amount from transaction, provider reconciliation | mismatched webhook goes to exception queue |
| Admin abuse or mistake | wrongful release/refund | reason required, audit events, dual control for high value where policy requires | audit event required |
| Dispute bypass | release during dispute | disputed escrow blocks release | release denied while disputed |
| Financing document exposure | sensitive financial data leak | private bucket, short-lived signed URLs, no public serializers | anonymous/cross-user denied |
| Consent bypass | unlawful data sharing | consent required before partner submission | partner submission denied without consent |
| Partner secret exposure | credential compromise | environment secrets only, never frontend, never logs | bundle/log secret scan |
| Unsafe raw payload storage | PII leakage | store hashes/minimal payload, encrypt raw payload if retained | serializer/log review |
| Provider outage | stuck workflow | status polling, admin reconciliation, retry queues | provider failure leaves transaction/application intact |
| Stale frontend state | user sees wrong financial status | backend-owned status, refetch after mutations | UI reflects API status |
| Race condition on state transitions | inconsistent escrow/review | database transactions and row locks | concurrent transition test |
| Overclaiming verified funding | user misled | explicit labels: pending, provider-confirmed, admin-confirmed | UI/status copy review |
| Rate-limit bypass | spam submissions/uploads | scoped throttles by user/IP/action | throttle tests |
| Malware upload | storage abuse | extension, MIME and content validation; no SVG by default | disguised executable rejected |

## Required Design Controls

1. Object-level permissions on every financial record.
2. Server-side party derivation.
3. Explicit state machines.
4. Immutable event ledgers for webhooks and audit actions.
5. Idempotency on external-facing actions.
6. Private storage for all proofs and financial documents.
7. Short-lived signed URLs.
8. Clear separation between payment proof, escrow funding, and financing decisions.
9. No provider secrets in JavaScript, OpenAPI examples, logs, or database.
10. Admin actions audited with reasons.

## High-Risk Workflows

### Escrow Release

Controls:

- funds must be confirmed by provider
- all required release conditions must be satisfied
- no active dispute
- release instruction idempotency
- provider confirmation required before final state
- admin/manual release requires reason

### Financing Partner Submission

Controls:

- applicant consent
- required documents
- active product and partner
- idempotent submission
- private application data
- partner response signature validation where webhooks exist

### File Access

Controls:

- storage key not exposed publicly
- signed URL generated only after object permission check
- short expiry
- no public bucket policy for proofs, escrow files, financing documents, or construction evidence

## Logging Rules

Allowed in logs:

- record id
- user id
- provider slug
- status transition
- error class
- request id

Never log:

- provider secrets
- signed URLs
- raw financing documents
- bank statements
- card/bank account details
- webhook secrets
- full raw provider payloads with PII

## Verification Checklist

- Backend permission tests cover participant and cross-user cases.
- Admin endpoints reject normal users.
- Webhook tests cover invalid signatures and replay.
- Secret scan covers frontend bundles and backend logs.
- Upload tests reject executable/script content.
- OpenAPI does not expose secret fields.
- Audit events exist for release, refund, dispute, consent, partner submission, and admin override.

