# RealityNG Escrow Reconciliation Runbook

## Purpose

Reconciliation compares RealityNG's expected escrow state with provider-reported state.

## Supported Outcomes

- `matched`
- `mismatch`
- `pending_review`
- `resolved`

## Manual Reconciliation Steps

1. Open the escrow record.
2. Compare expected funded amount with partner-confirmed amount.
3. Compare RealityNG status with provider status.
4. Record reconciliation result.
5. If mismatch exists, document details.
6. Do not overwrite financial state automatically.
7. Resolve only after partner evidence is reviewed.

## Mismatch Examples

- provider confirms lower amount than RealityNG expected
- provider reference does not match the transaction
- provider reports refunded while RealityNG shows release pending
- duplicate webhook delivery without matching ledger state

## Production Activation Requirement

Before production activation, the partner must provide either:

- a reconciliation API, or
- a daily reconciliation export, or
- an approved manual confirmation process.

