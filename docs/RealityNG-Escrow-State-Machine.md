# RealityNG Escrow State Machine

## EscrowTransaction Statuses

- `draft`
- `awaiting_provider`
- `awaiting_funding`
- `partially_funded`
- `funded`
- `conditions_pending`
- `release_pending`
- `released`
- `refund_pending`
- `refunded`
- `disputed`
- `cancelled`
- `failed`

## Funding Authority

Funding is never confirmed by the frontend. Valid authorities are:

- provider webhook
- provider API verification
- audited manual provider confirmation

Payment proof remains separate from escrow funding.

## Release Flow

1. Escrow is funded by provider confirmation.
2. Required conditions are satisfied.
3. Buyer or authorized manager requests release.
4. Owner/admin/authorized manager approves release.
5. Provider instruction is recorded.
6. Provider settlement confirmation is recorded.
7. Escrow becomes `released`.

The release request alone never marks escrow as released.

## Refund Flow

1. Buyer/admin/authorized manager requests refund with reason.
2. Owner/admin/authorized manager approves refund.
3. Provider instruction is recorded.
4. Provider refund confirmation is recorded.
5. Escrow becomes `refunded`.

The refund request alone never marks escrow as refunded.

## Dispute Rule

An open or under-review `PaymentDispute` blocks release. This only blocks RealityNG's release workflow. It does not claim that external funds are frozen unless a provider confirms that separately.

## Reconciliation Rule

Reconciliation mismatches create review records and set `reconciliation_status=mismatch`. They do not overwrite escrow financial state automatically.

