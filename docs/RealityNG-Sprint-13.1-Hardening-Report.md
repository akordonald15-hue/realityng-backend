# RealityNG Sprint 13.1 Hardening Report

## Executive Summary

Sprint 13.1 hardens the existing messaging and notification foundation. The
core Sprint 13 models, REST APIs, WebSocket consumers, Redis channel layer,
notification preferences and email provider abstraction are preserved.

## Completed Hardening

- Added durable realtime outbox records for message and notification broadcasts.
- Added retryable Celery processing for realtime outbox events.
- Added message send idempotency with `client_message_id`.
- Added user-scoped WebSocket message throttling.
- Disabled query-string WebSocket JWT authentication by default.
- Added reconnect sync support through `?after={message_id}`.
- Preserved PostgreSQL as the source of truth for messages and notifications.
- Added structured log labels for realtime, auth, throttle and outbox failures.
- Added frontend client-generated message IDs, dedupe and reconnect sync.
- Added paginated message-history support in the frontend.

## Current Send Path

```text
request/socket
  -> authorization
  -> Message saved
  -> Notification saved
  -> AuditLog saved
  -> RealtimeOutboxEvent saved
  -> transaction commit
  -> Celery outbox processing
  -> Redis/Channels group_send
```

## Deferred

- Device-level delivery receipts.
- Typing indicators.
- Presence.
- Attachments.
- Push/SMS delivery.

## Validation Notes

Local SQLite checks are used for iterative validation on Windows. PostgreSQL and
Redis validation must be run in Docker/CI before merge approval if the local
shell cannot reach the Docker network hostnames.
