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
- Dual approval threshold is planned but not fully enforced in this implementation pass.
- PostgreSQL validation used an isolated local PostgreSQL 18 cluster because Docker Desktop was unavailable.
- Redis was unavailable locally, so PostgreSQL regression tests used a temporary validation settings module with in-memory cache/channel layers.

## Validation Notes

- Ruff: passed locally.
- Django check: passed locally against PostgreSQL.
- Makemigrations check: passed locally against PostgreSQL.
- Clean migration: passed locally against PostgreSQL.
- Upgrade migration from `payments.0001` to `payments.0002`: passed locally against PostgreSQL.
- OpenAPI: 0 errors, 11 existing enum warnings remain.
- Payments tests: 47 passed on PostgreSQL.
- Full backend suite: 344 passed on PostgreSQL.
- Direct behavior smoke: webhook replay, uniqueness constraints, release/refund idempotency, row locking, large Decimal values, partial funding and provider confirmation transitions passed.

## Defects Fixed During PostgreSQL Gate

- Fixed a release/refund race where a refund request could be created after an active release request.
- Fixed idempotent release/refund retries so the existing action is returned after escrow status changes.
- Added regression tests for duplicate release/refund requests and conflicting active release/refund states.
