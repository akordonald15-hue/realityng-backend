# RealityNG Sprint 13 - Notifications, Messaging and Realtime Communication

## Executive Summary

Sprint 13 completes the notification and messaging foundation on top of the already integrated
HTTP APIs. The backend now supports in-app notifications, preference-aware notification creation,
transactional email hooks, audited messaging actions, thread unread counts, and authenticated
WebSocket delivery through Django Channels.

The implementation preserves the existing Sprint 12 lead workflow and extends it by emitting lead
stage notifications from the existing inquiry pipeline rather than creating a duplicate CRM
messaging model.

## Backend Changes

- Added Django Channels, Daphne, and channels-redis dependencies.
- Configured ASGI with HTTP and WebSocket routing.
- Added Redis-backed channel-layer settings:
  - `CHANNEL_LAYER_REDIS_URL`
  - `CHANNEL_LAYER_PREFIX`
- Added authenticated WebSocket middleware using JWT access tokens supplied through the
  `Sec-WebSocket-Protocol` subprotocol list.
- Added WebSocket consumers:
  - `/ws/notifications/`
  - `/ws/messages/threads/{thread_id}/`
- Added message and participant indexes for deterministic thread/message lookup.
- Added preference-aware notification service functions.
- Added transactional email foundation:
  - provider abstraction in `apps.notifications.email`
  - Celery task hook in `apps.notifications.tasks`
  - `NOTIFICATION_EMAIL_TASKS_ENABLED` environment switch
- Added audited message send and read actions.
- Added unread message count support.
- Paginated thread message history.
- Updated lead pipeline transitions to emit the existing `LeadStageChanged` notification event.

## Security

- WebSocket connections require authenticated JWT access.
- Thread WebSocket access is limited to existing conversation participants.
- Non-participants receive a denied WebSocket connection.
- HTTP thread/message APIs remain participant-scoped.
- Message sender spoofing remains blocked; the backend uses `request.user`.
- Notification preferences are scoped to the current authenticated user.
- Access tokens are supported in the WebSocket subprotocol list so the frontend does not need to
  place tokens in WebSocket URLs.

## Email Foundation

The sprint does not configure a production email provider. It provides a provider-shaped
foundation around Django mail and queues email work through Celery after the notification row is
committed.

In local/debug environments, `NOTIFICATION_EMAIL_TASKS_ENABLED` defaults to `false` to prevent test
and development runs from hanging when a Celery broker is not available. Production should set it
to `true` after the email provider and worker process are configured.

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `CHANNEL_LAYER_REDIS_URL` | Redis URL used by Django Channels. Defaults to `REDIS_URL`. |
| `CHANNEL_LAYER_PREFIX` | Redis channel-layer key prefix. Defaults to `realityng`. |
| `NOTIFICATION_EMAIL_TASKS_ENABLED` | Enables Celery email task queueing. Defaults to `false` when `DEBUG=true`, otherwise `true`. |

## Validation

Local validation used an SQLite override because the Windows shell could not resolve the Docker
PostgreSQL hostname `postgres` outside the Compose network.

- Ruff targeted check: passed.
- Django check: passed.
- `makemigrations --check --dry-run`: passed.
- Clean `migrate --noinput`: passed.
- OpenAPI validation: 0 errors, 9 existing enum warnings.
- Notification/API/WebSocket tests: 15 passed.

## Known Limitations

- Production email delivery still requires provider credentials, sender-domain setup, and worker
  deployment validation.
- WebSocket production rollout requires the deployment stack to route upgrade requests to the ASGI
  application.
- Full PostgreSQL regression should be run in a Docker/CI/staging environment where the PostgreSQL
  service is reachable from the test runner.

## Sprint 14 Readiness

Sprint 14 can build notification delivery channels, richer messaging UX, or communication
analytics on top of this foundation without replacing the conversation, preference, or realtime
architecture.
