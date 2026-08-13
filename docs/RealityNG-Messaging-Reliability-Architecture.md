# RealityNG Messaging Reliability Architecture

Sprint 13.1 hardens the existing Sprint 13 communication foundation without
rewriting it.

## Components

- PostgreSQL: durable source of truth for threads, participants, messages,
  notifications, preferences and realtime outbox events.
- Realtime outbox: records delivery intent in the same transaction as the
  message or notification.
- Celery: processes pending realtime outbox events and retries transient
  broadcast failures.
- Redis/Channels: realtime transport for online clients.
- HTTP sync: recovery path for missed messages after reconnect or offline use.

## Send Path

```text
HTTP or WebSocket request
  -> authenticate and authorize participant
  -> validate body and client_message_id
  -> create Message
  -> create Notification rows for recipients
  -> create AuditLog
  -> create RealtimeOutboxEvent rows
  -> commit
  -> enqueue Celery outbox processing
  -> publish to Redis/Channels
```

If Celery or Redis is unavailable, the message remains committed in PostgreSQL.
The outbox row remains retryable.

## Idempotency

`Message.client_message_id` is a client-generated UUID. The database enforces
one message per:

```text
thread + sender + client_message_id
```

Retries with the same client ID return the original message and do not create
duplicate notifications or audit events.

## Rate Limiting

HTTP sends keep using DRF throttles. WebSocket sends use a server-side cache
counter scoped by authenticated user, so multiple sockets do not multiply a
user's allowance.

Configuration:

- `WEBSOCKET_MESSAGE_RATE_LIMIT_COUNT`
- `WEBSOCKET_MESSAGE_RATE_LIMIT_WINDOW_SECONDS`

## Observability

Sprint 13.1 adds stable log labels for:

- `message.idempotency.hit`
- `realtime.broadcast.failed`
- `realtime.broadcast.retried`
- `realtime.outbox.dead`
- `websocket.auth.failed`
- `websocket.thread_join.denied`
- `websocket.rate_limited`

Logs avoid JWTs, credentials and full private message bodies.

## Deferred

Device-level delivery receipts, typing indicators, presence and attachments are
not part of Sprint 13.1.
