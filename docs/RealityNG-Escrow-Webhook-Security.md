# RealityNG Escrow Webhook Security

## Intake Flow

1. Resolve provider by server-side route slug.
2. Hash request body.
3. Verify configured signature.
4. Persist webhook ledger record.
5. Reject invalid signatures.
6. Check provider event id for replay.
7. Process domain state through escrow services only.

## Signature Header

Current internal header:

```text
X-RealityNG-Escrow-Signature
```

Production providers may require provider-specific signature headers. Add those in the adapter, not directly in the view.

## Replay Protection

`ProviderWebhookEvent` enforces a unique live `(provider, provider_event_id)` pair.

Duplicate delivery must not create duplicate:

- funding events
- releases
- refunds
- settlements
- audit events
- notifications

## Payload Rules

The implementation stores `payload_hash`, not raw financial payloads by default.

Never log:

- provider secrets
- signed URLs
- raw sensitive payloads
- private documents
- bank details

