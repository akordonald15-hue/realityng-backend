# RealityNG Escrow Provider Adapter

## Purpose

Escrow provider adapters isolate RealityNG's domain services from partner-specific SDKs or APIs.

## Interface

The adapter boundary supports:

- `create_escrow`
- `request_release`
- `request_refund`
- `fetch_status`
- `verify_webhook`

## Current Modes

### Manual

Manual mode records partner references, funding, release, refund, settlement and reconciliation through audited operations. It is intended for early operational workflows where the partner does not provide a full API.

Manual mode is not permission to fabricate provider confirmation. Each action requires a provider reference or operational note where applicable.

### Sandbox

Sandbox mode is a safe placeholder adapter for lifecycle testing. It does not activate real money movement.

### API

API mode is reserved for future licensed provider integrations after legal/compliance approval and sandbox certification.

## Secrets

Provider secrets must come from environment variables or a secrets manager. They must not be stored on `EscrowProvider`.

Webhook secret naming convention:

```text
ESCROW_<PROVIDER_SLUG>_WEBHOOK_SECRET
```

The provider slug is uppercased and hyphens are replaced with underscores.

