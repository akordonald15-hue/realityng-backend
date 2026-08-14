# RealityNG Sprint 14.1 Escrow Implementation Report

Status: Implementation branch  
Branch: `feature/sprint-14.1-escrow`  
Production provider: not activated

## Executive Summary

Sprint 14.1 adds provider-backed escrow orchestration on top of the Sprint 14 transaction foundation. The implementation keeps `Transaction`, `PaymentMilestone`, `PaymentProof`, and `PaymentDispute` intact, then attaches an `EscrowTransaction` one-to-one where escrow tracking is required.

RealityNG does not custody money in this implementation. Funding, release, refund, and settlement states are recorded as partner-confirmed or audited manual-provider operations.

## Models Added

- `EscrowProvider`
- `EscrowTransaction`
- `EscrowFundingEvent`
- `EscrowCondition`
- `EscrowRelease`
- `EscrowRefund`
- `EscrowSettlement`
- `EscrowSettlementAllocation`
- `ProviderWebhookEvent`
- `EscrowReconciliationRecord`

## Core Capabilities

- provider metadata and capability tracking
- manual/sandbox/API adapter abstraction
- escrow creation against existing transactions
- provider reference recording
- provider-confirmed funding events
- partial funding support
- extensible release conditions
- optional inspection and construction milestone condition links
- release request, approval, provider instruction, and provider confirmation
- refund request, approval, provider instruction, and provider confirmation
- settlement and allocation records
- webhook ledger with signature status and replay protection
- reconciliation records without automatic state overwrite
- dedicated `manage_transactions` property assignment capability
- scoped escrow throttles

## Security Controls

- buyers cannot self-confirm funding
- frontend cannot mass-assign escrow financial state
- release/refund confirmation requires provider/manual confirmation reference
- duplicate provider funding events are idempotent
- duplicate release/refund requests support idempotency keys
- open disputes block release
- assigned managers require explicit transaction capability
- admin/manager operational actions are auditable
- provider secrets are not stored in database models

## API Summary

- `GET /api/v1/escrow-providers/`
- `GET /api/v1/payment-escrows/`
- `GET /api/v1/payment-escrows/{id}/`
- `POST /api/v1/transactions/{id}/escrow/`
- `GET /api/v1/transactions/{id}/escrow/`
- `POST /api/v1/payment-escrows/{id}/record-provider-reference/`
- `POST /api/v1/payment-escrows/{id}/record-funding/`
- `POST /api/v1/payment-escrows/{id}/conditions/`
- `POST /api/v1/payment-escrows/{id}/satisfy-condition/`
- `POST /api/v1/payment-escrows/{id}/request-release/`
- `POST /api/v1/payment-escrows/{id}/approve-release/`
- `POST /api/v1/payment-escrows/{id}/confirm-release/`
- `POST /api/v1/payment-escrows/{id}/request-refund/`
- `POST /api/v1/payment-escrows/{id}/approve-refund/`
- `POST /api/v1/payment-escrows/{id}/confirm-refund/`
- `POST /api/v1/payment-escrows/{id}/record-settlement/`
- `POST /api/v1/payment-escrows/{id}/reconcile/`
- `POST /api/v1/escrow-webhooks/{provider_slug}/`

## Known Limitations

- No live financial provider is configured.
- Manual provider mode is implemented for controlled operations.
- Sandbox adapter is a local abstraction, not a real external sandbox.
- PostgreSQL validation still needs to be repeated in an isolated Compose stack before merge approval.
- Dual approval threshold is planned but not fully enforced in this implementation pass.
- Full-project pytest did not complete within the local Windows validation timeout; the changed payments surface passed.

## Validation Notes

- Ruff: passed locally.
- Django check: passed locally.
- Makemigrations check: passed locally.
- Clean migration: passed locally using disposable SQLite.
- OpenAPI: 0 errors, 11 existing enum warnings remain.
- Payments tests: 43 passed.
- Direct service smoke: escrow create, funding, condition, release approval and confirmation passed.
- Full backend suite: attempted locally, timed out before completion.
