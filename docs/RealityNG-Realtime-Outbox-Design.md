# RealityNG Realtime Outbox Design

## Purpose

The realtime outbox decouples durable user actions from Redis availability.
Messages and notifications are committed to PostgreSQL first. Realtime delivery
is retried separately.

## Model

`RealtimeOutboxEvent` stores:

- `event_type`
- `aggregate_type`
- `aggregate_id`
- optional `recipient_user`
- optional `conversation_thread`
- `payload`
- `status`
- `attempt_count`
- `next_attempt_at`
- `last_error`
- `processed_at`

Supported event types:

- `message.created`
- `notification.created`

Statuses:

- `pending`
- `processing`
- `delivered`
- `failed`
- `dead`

## Transaction Boundary

Outbox events are created inside the same transaction as the message or
notification. The Celery worker is queued only after commit.

## Processing

`notifications.process_realtime_outbox_event` processes one event.
`notifications.process_due_realtime_outbox_events` processes due pending or
failed events in batches.

## Retry Policy

Retries are bounded. Failed events move through delayed attempts and become
`dead` after exhausting the configured maximum attempts.

## Concurrency

Workers claim individual events with row locking before publishing. Delivered,
dead or currently processing events are not published again by a second worker.

## Idempotency

The outbox publishes already-persisted events only. It never creates another
message or notification. The model also enforces one outbox event per
`event_type + aggregate_id`.
