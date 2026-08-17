# RealityNG Launch Dependency Map

Status: planning locked

## Sequential Dependency

```text
v2.6.0
  |
  v
Sprint 15 - Software integrity, security, regression
  |
  v
Sprint 16 - Compliance, legal, trust
  |
  v
Sprint 17 - Dedicated infrastructure
  |
  v
Sprint 18 - Performance and capacity validation
  |
  v
Sprint 19 - Production content and UX readiness
  |
  v
Sprint 20 - Controlled beta
  |
  v
Public launch decision
```

## Hard Dependencies

| Work | Depends on | Reason |
| --- | --- | --- |
| Sprint 15 closure | Stable PostgreSQL/Redis validation environment | v2.6.0 full backend PostgreSQL suite follow-up must be closed. |
| Sprint 16 high-risk copy approval | Legal/privacy/financial review | Escrow, financing, verification, inspection, construction, and data-retention wording need professional approval. |
| Sprint 17 production migration | Sprint 15 blocker review | Infrastructure should not be migrated with unknown critical security or data issues. |
| Sprint 18 load testing | Staging or disposable infrastructure | Heavy load testing must not run on the shared Caretekk VPS. |
| Sprint 19 launch content | Sprint 16 approved wording | Public content must reflect legal and financial boundaries. |
| Sprint 20 beta | Gates A-E | Beta starts only when software, compliance, infrastructure, performance, and product readiness are acceptable. |

## Safe Parallel Work

| Parallel stream | Can start during | Guardrail |
| --- | --- | --- |
| Legal document drafting | Sprint 15 | Use draft status until professional approval. |
| Infrastructure vendor/cost review | Sprint 15 | No production migration until Sprint 17. |
| Content inventory | Sprint 15 | Do not publish high-risk wording before Sprint 16. |
| Browser/device matrix preparation | Sprint 15 | Execution can continue into Sprint 19. |
| Load-test script planning | Sprint 17 | Execution waits for staging/dedicated environment. |

## Current Known Follow-Up

The v2.6.0 post-merge full backend PostgreSQL suite timed out locally after release. Earlier pre-merge validation reached `361 passed`. Sprint 15 owns this closure.

