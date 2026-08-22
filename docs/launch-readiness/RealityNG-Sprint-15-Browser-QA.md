# RealityNG Sprint 15 Browser QA

Status: passed

Date: 2026-08-22

## Execution Environment

The gate used Playwright 1.62.1 with installed Google Chrome 151.0.7922.170 at
`C:\Program Files\Google\Chrome\Application\chrome.exe`. Playwright did not
download or use a bundled browser. The frontend and Django/Daphne backend ran on
loopback addresses against isolated PostgreSQL, Redis and MinIO services. API
mocks were disabled. Realtime outbox tasks executed eagerly for deterministic QA
delivery while still using the real Redis channel layer.

Synthetic users and records were created idempotently by
`seed_sprint15_browser_qa`. Runtime JWT values and signed URLs are excluded from
committed artifacts and documentation.

## Results

| Surface | 1440x900 | 1366x768 | 768x1024 | 390x844 | 360x800 |
| --- | --- | --- | --- | --- | --- |
| Home, public navigation and authentication | PASS | PASS | PASS | PASS | PASS |
| Property and provider discovery | PASS | PASS | PASS | PASS | PASS |
| Authenticated launch surfaces and overflow | PASS | PASS | PASS | PASS | PASS |
| Persona, admin and financial journeys | PASS | Desktop gate | Desktop gate | Desktop gate | Desktop gate |
| Messaging, notifications and WebSockets | PASS | Desktop gate | Desktop gate | Desktop gate | Desktop gate |

The final `npm run test:e2e` execution passed 18 real-browser cases and skipped
32 intentional non-desktop duplicates. Desktop cases exercised authenticated
buyer, owner, manager, revoked-manager, inspector, provider and admin journeys,
private signed-document authorization, financial wording and negative access.

The WebSocket case used two authenticated browser contexts. Chrome observed an
HTTP 101 upgrade, JWT transport through `Sec-WebSocket-Protocol`, no token in the
URL, bidirectional message delivery, notification delivery, offline recovery,
reconnect deduplication and a denied nonparticipant connection. Tokens and
signed URLs were inspected only in memory and were never persisted.

Console errors, uncaught page errors, failed requests and unexpected HTTP
statuses were gate failures. Expected negative 400/401/403/404 responses were
narrowly allowlisted and asserted. Passing screenshots are retained under the
ignored local `test-results/` directory. Evidence includes public property,
buyer dashboard, inspection assignment, transaction/escrow, financing,
admin-financing queue and mobile dashboard screenshots. Traces are retained
only on failure.

Microsoft Edge was not executed and is optional/nonblocking for this gate.
