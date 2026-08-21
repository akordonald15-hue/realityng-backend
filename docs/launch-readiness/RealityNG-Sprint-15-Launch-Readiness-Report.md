# RealityNG Sprint 15 Launch Readiness Report

Status: engineering security work complete; merge gate pending visual QA  
Date: 2026-08-21

## Completed

- Closed the v2.6.0 full PostgreSQL regression follow-up: 361 passed baseline.
- Passed frontend lint, typecheck, 46-file/91-test suite, mock build and real API build.
- Moved local host bindings to configurable loopback-only ports without changing
  container networking.
- Started PostgreSQL, Redis and MinIO successfully in the isolated compose stack.
- Added and verified the missing financing-document private bucket.
- Proved every sensitive bucket private and every storage backend signed,
  expiring and non-overwriting.
- Audited authorization, property assignments, finance and realtime controls.
- Fixed S15-AUTH-001, a former-inspector access defect.
- Expanded signed-URL and WebSocket security regressions.
- Passed the final full PostgreSQL regression: 369 tests, 0 failures, 262
  warnings in 593.18 seconds.

## Environment

Default host ports are PostgreSQL 55432, Redis 56379, MinIO API 59000, MinIO
console 59001, and backend 58000. All bind to `127.0.0.1`; environment variables
can override them. Container service URLs and standard internal ports remain
unchanged. Credentials are environment-driven with local-only defaults.

## Defects

| ID | Severity | State | Summary |
| --- | --- | --- | --- |
| S15-INFRA-001 | Medium | Fixed | Compose host PostgreSQL collision |
| S15-STORAGE-001 | High | Fixed | Financing bucket absent/mismatched across compose and settings |
| S15-AUTH-001 | High | Fixed | Inactive inspection assignment retained private access |
| S15-QA-001 | Medium | Open | Visual desktop/tablet/mobile QA blocked by unavailable browser session |

## Remaining Launch Risks

- Visual browser/responsive QA is not complete.
- Malware scanning/quarantine is not implemented.
- Backup restore and production rollback rehearsal remain later infrastructure/
  beta gates and must not run destructively on the shared VPS.
- Legal/privacy/financial approvals remain Sprint 16 work.
- Dedicated infrastructure and staging remain Sprint 17 prerequisites.

## Assessment

Sprint 15 code and automated security gates are suitable for review. Merge is
not recommended until S15-QA-001 is completed or explicitly accepted by
leadership under the launch blocker policy.
