# RealityNG Sprint 15 Regression Closure

Status: closed  
Baseline: backend `70e5fcd`, frontend `925ef8b`  
Environment: isolated PostgreSQL 16 and Redis 7 on loopback-only ports

## Baseline Evidence

| Gate | Result |
| --- | --- |
| Backend Ruff | PASS |
| Django check | PASS, 0 issues |
| Migration drift | PASS, no changes detected |
| Migration plan/application | PASS on PostgreSQL |
| OpenAPI | PASS, 0 errors and 12 known enum warnings |
| Full backend PostgreSQL suite | PASS, 361 passed before Sprint 15 changes |
| Frontend lint/typecheck | PASS |
| Frontend tests | PASS, 46 files and 91 tests |
| Mock/real API builds | PASS |
| Redis/Channels/Celery/Beat/ASGI | PASS |

The v2.6.0 post-merge PostgreSQL timeout follow-up is closed. After Sprint 15
changes, the full PostgreSQL suite passed with 369 tests and 262 warnings in
593.18 seconds. The eight-test increase is three inactive-inspection assignment
states, two private-storage invariants, and three WebSocket security cases.
