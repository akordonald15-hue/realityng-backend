# RealityNG Sprint 14.1 Escrow Architecture Plan

Status: Planning only  
Source branch reviewed: `integration/sprint-14-review`  
Implementation rule: do not connect a real provider until legal, finance, and partner approvals are complete.

## Executive Summary

Sprint 14 currently provides a safe transaction foundation: transactions, milestones, payment proofs, disputes, private proof storage, signed access, permissions, throttles, admin review, and audit coverage. Sprint 14.1 should extend that foundation into provider-backed escrow without replacing it.

The recommended approach is to keep `Transaction` as the commercial record of intent and add an escrow layer around it. RealityNG should not hold funds directly in the MVP. A licensed escrow/payment partner should custody funds, send webhook events, confirm funding, receive release/refund instructions, and provide reconciliation data.

## Existing Foundation To Reuse

Reuse:

- `apps.payments.Transaction`
- `PaymentMilestone`
- `PaymentProof`
- `PaymentDispute`
- existing payment permissions and assignment-aware property authorization
- private proof-storage pattern
- signed URL access pattern
- audit/event conventions
- notification/outbox conventions from Sprint 13
- inspections from Sprint 10
- construction milestones from Sprint 11
- lead/application transaction creation rules from Sprint 12/14

Do not create a separate disconnected escrow transaction model that can drift from `Transaction`.

## Domain Model Plan

### EscrowProvider

Represents an external partner or a manual escrow operator.

Suggested fields:

- `id`
- `name`
- `slug`
- `status`: `draft`, `sandbox`, `active`, `disabled`
- `integration_mode`: `manual`, `api`, `hybrid`
- `supported_currencies`
- `minimum_amount`
- `maximum_amount`
- `supports_split_settlement`
- `supports_partial_release`
- `supports_refund`
- `webhook_identifier`
- `created_at`
- `updated_at`

Do not store provider secrets directly in the model. Use environment variables or a secrets manager.

### EscrowTransaction

One-to-one extension of `Transaction`.

Suggested fields:

- `transaction`
- `provider`
- `external_reference`
- `status`
- `currency`
- `expected_amount`
- `funded_amount`
- `platform_fee_amount`
- `seller_settlement_amount`
- `reconciliation_status`
- `provider_state`
- `initiated_by`
- `initiated_at`
- `funded_at`
- `released_at`
- `refunded_at`
- `cancelled_at`
- `metadata`
- `created_at`
- `updated_at`

Recommended statuses:

- `not_started`
- `initiated`
- `awaiting_funding`
- `funded`
- `conditions_pending`
- `release_requested`
- `partially_released`
- `released`
- `refund_requested`
- `refunded`
- `disputed`
- `cancelled`
- `failed`

### EscrowFundingEvent

Immutable provider funding evidence.

Suggested fields:

- `escrow_transaction`
- `provider_event_id`
- `event_type`
- `amount`
- `currency`
- `status`
- `received_at`
- `effective_at`
- `idempotency_key`
- `payload_hash`
- `processing_status`
- `created_at`

Unique constraint:

- `(provider, provider_event_id)`

### EscrowCondition

Represents a release precondition.

Suggested fields:

- `escrow_transaction`
- `condition_type`
- `title`
- `description`
- `status`
- `required`
- `source_app`
- `source_model`
- `source_object_id`
- `satisfied_by`
- `satisfied_at`
- `due_at`
- `created_at`
- `updated_at`

Condition types:

- `buyer_confirmation`
- `seller_documentation`
- `property_verification`
- `inspection_completed`
- `construction_milestone_completed`
- `admin_approval`
- `dispute_resolved`

Keep the typed source reference explicit and validated. Avoid unconstrained generic references unless the codebase already has a safe attachment abstraction.

### EscrowRelease

Release instruction and confirmation.

Suggested fields:

- `escrow_transaction`
- `amount`
- `currency`
- `requested_by`
- `authorized_by`
- `provider_instruction_id`
- `status`
- `reason`
- `requested_at`
- `instructed_at`
- `confirmed_at`
- `failed_at`
- `idempotency_key`
- `created_at`

Statuses:

- `draft`
- `requested`
- `approved`
- `sent_to_provider`
- `confirmed`
- `failed`
- `cancelled`

### EscrowRefund

Refund instruction and confirmation.

Suggested fields mirror `EscrowRelease`, with refund-specific reason and beneficiary.

### EscrowSettlement

Captures final allocation.

Suggested fields:

- `escrow_transaction`
- `gross_amount`
- `platform_fee_amount`
- `seller_amount`
- `partner_fee_amount`
- `tax_amount`
- `status`
- `settled_at`
- `created_at`

### EscrowWebhookEvent

Provider webhook intake ledger.

Suggested fields:

- `provider`
- `provider_event_id`
- `event_type`
- `signature_valid`
- `payload_hash`
- `processing_status`
- `received_at`
- `processed_at`
- `error_message`
- `retry_count`

Store minimal raw payload data. If raw provider payloads are retained, protect them as sensitive operational records.

## State Machine

| From | To | Actor | Preconditions | Side effects |
| --- | --- | --- | --- | --- |
| `not_started` | `initiated` | buyer, admin, system | linked transaction is valid | audit event, partner session/manual record |
| `initiated` | `awaiting_funding` | system | provider reference created | notify buyer/seller |
| `awaiting_funding` | `funded` | webhook/admin reconciliation | funding event matches expected amount | funding event recorded, audit |
| `funded` | `conditions_pending` | system | at least one required condition exists | condition checklist visible |
| `conditions_pending` | `release_requested` | buyer/admin/system | all required conditions satisfied | release request event |
| `release_requested` | `released` | provider webhook/admin reconciliation | provider confirms settlement | settlement recorded, transaction updated |
| any active | `disputed` | buyer, seller, admin | dispute submitted or admin hold | release locked |
| `disputed` | `conditions_pending` | admin | dispute resolved without release/refund | audit |
| `disputed` | `refund_requested` | admin | refund approved | provider refund instruction |
| `awaiting_funding` | `cancelled` | buyer/admin/system | no funding or expired session | audit |

Direct arbitrary status PATCH operations must not be allowed.

## Provider Integration Pattern

Create a provider adapter interface:

- `create_escrow_reference`
- `verify_funding_event`
- `request_release`
- `request_refund`
- `fetch_transaction_status`
- `fetch_reconciliation_report`

Adapters must be idempotent. Each provider call should include an idempotency key and persist the request/response state.

Initial implementation can support:

1. `manual` provider for controlled internal escrow review.
2. `sandbox` API provider when a real partner is selected.
3. `production` API provider only after legal and finance approval.

## API Surface

| Endpoint | Purpose | Auth |
| --- | --- | --- |
| `POST /api/v1/payments/transactions/{id}/escrow/initiate/` | start escrow for a transaction | buyer/admin/authorized participant |
| `GET /api/v1/payments/transactions/{id}/escrow/` | escrow detail | transaction participant/admin |
| `GET /api/v1/payments/transactions/{id}/escrow/conditions/` | release checklist | transaction participant/admin |
| `POST /api/v1/payments/transactions/{id}/escrow/conditions/{condition_id}/satisfy/` | mark manual/admin condition satisfied | admin or authorized system actor |
| `POST /api/v1/payments/transactions/{id}/escrow/release/` | request release | buyer/admin according to policy |
| `POST /api/v1/payments/transactions/{id}/escrow/refund/` | request refund | admin or policy-controlled actor |
| `POST /api/v1/payments/webhooks/{provider_slug}/` | receive provider events | signed provider requests only |
| `GET /api/v1/payments/admin/escrow/` | admin queue | admin |
| `GET /api/v1/payments/admin/escrow/{id}/` | admin detail | admin |
| `POST /api/v1/payments/admin/escrow/{id}/reconcile/` | reconcile against provider state | admin |

## Integration With Inspections And Construction

Escrow conditions should be satisfied by existing domain events:

- inspection report approved
- property verification approved
- construction milestone completed after required inspection gate
- buyer handover confirmation
- admin dispute resolution

Do not duplicate inspection reports or construction milestone state in the escrow app. Reference and verify the authoritative record.

## Permissions

Backend permissions remain authoritative.

Allowed participants:

- buyer/customer attached to the transaction
- property owner/seller
- assigned manager with explicit property capability
- admin

Denied:

- unrelated agent
- revoked assignment
- suspended assignment
- unrelated buyer
- anonymous user

Never allow the frontend to decide whether funds can be released.

## Security Requirements

- Webhooks must verify provider signature.
- Webhook events must be idempotent.
- Amount and currency must be validated server-side.
- Release/refund operations must be idempotent.
- Admin manual overrides must require reason and audit event.
- Escrow state transitions must be explicit.
- Provider secrets must not enter frontend bundles, logs, OpenAPI examples, or database records.
- Signed document URLs must remain short-lived.
- Disputed escrow must block release unless admin resolves it.

## Database And Migration Plan

Recommended migration sequence:

1. Add provider and escrow core models.
2. Add escrow conditions, release, refund, funding events.
3. Add webhook ledger and reconciliation records.
4. Add indexes and constraints.
5. Add admin registrations and serializers.
6. Add provider adapter service layer.
7. Add API routes and tests.

High-value indexes:

- escrow status
- provider reference
- transaction relation
- webhook provider event id
- release/refund status
- condition status

## Test Plan

Backend tests:

- participant authorization
- assignment-aware authorization
- state transition validity
- webhook signature rejection
- webhook idempotency
- duplicate funding event prevention
- amount mismatch handling
- release condition enforcement
- release idempotency
- refund idempotency
- dispute blocks release
- admin override audit
- OpenAPI validation
- PostgreSQL migration validation

## Open Questions

- Which licensed partner will custody escrow funds?
- Is RealityNG permitted to initiate release/refund instructions, or only record partner decisions?
- What exact buyer/seller terms govern release conditions?
- What fees are charged, and when are they recognized?
- What dispute SLA applies before release/refund?
- What reconciliation file/API format will the partner provide?
- Are partial releases allowed for construction milestones?
- What regulatory obligations apply in Nigeria for escrow facilitation?

## Recommended Build Order

1. Provider-agnostic model and state machine.
2. Manual escrow mode.
3. Admin escrow queue and reconciliation.
4. Webhook intake ledger.
5. Sandbox provider adapter.
6. Public transaction escrow UI.
7. Production provider activation after approvals.

