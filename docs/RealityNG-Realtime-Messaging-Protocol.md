# RealityNG Realtime Messaging Protocol

## Connection

Clients connect to:

- `ws/notifications/`
- `ws/messages/threads/{thread_id}/`

Authentication uses the WebSocket subprotocol list:

- `realityng.websocket.v1`
- `access_token.{JWT_ACCESS_TOKEN}`

Production disables query-string token authentication by default with:

- `WEBSOCKET_ALLOW_QUERY_TOKEN=false`

## Message Send

Client event:

```json
{
  "type": "message.send",
  "body": "Hello",
  "client_message_id": "uuid"
}
```

`client_message_id` is an idempotency key scoped to sender and thread.

Server acceptance:

```json
{
  "type": "message.accepted",
  "message_id": "uuid",
  "client_message_id": "uuid"
}
```

Server broadcast:

```json
{
  "type": "message.created",
  "message": {
    "id": "uuid",
    "thread": "uuid",
    "sender": "uuid",
    "body": "Hello",
    "client_message_id": "uuid",
    "edited_at": null,
    "created_at": "iso8601"
  }
}
```

## Errors

Rate limits return a structured event and keep the socket open:

```json
{
  "type": "error",
  "code": "rate_limited",
  "detail": {
    "message": "Too many messages. Try again shortly.",
    "retry_after_seconds": 10
  }
}
```

## Reconnect Sync

WebSocket delivery is not durable storage. On reconnect, clients call:

```text
GET /api/v1/messages/threads/{thread_id}/messages/?after={message_id}
```

The API returns messages newer than the cursor in server order. Clients merge by
`id` and `client_message_id` to avoid duplicates.

## Degraded Mode

PostgreSQL is the source of truth. If Redis/Channels delivery is unavailable,
messages and notifications remain persisted and realtime outbox events remain
pending or failed for retry. Clients can still recover missed messages through
HTTP history and sync.
