# RealityNG Launch Risk Register

Status: initial launch register

| Risk | Severity | Likelihood | Impact | Existing mitigation | Remaining mitigation | Owner | Launch blocker? | Verification method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IDOR exposes private user, property, service, inspection, construction, or financial records | Critical | Medium | Severe privacy/security incident | Object permission tests exist in multiple domains | Sprint 15 adversarial IDOR matrix | Engineering/Security | Yes | API tests and manual guessed-ID attempts |
| Private financial document leakage | Critical | Medium | Severe privacy/compliance incident | Private storage, signed URL endpoints, authorization checks | Sprint 15 private data audit and Sprint 16 retention policy | Engineering/Security/Legal | Yes | Signed URL and serializer tests |
| Financial wording implies RealityNG is lender/custodian | Critical | Medium | Legal/regulatory exposure | Architecture docs define marketplace boundary | Sprint 16 legal review and Sprint 19 content audit | Product/Legal | Yes | Copy review and approval |
| Escrow/financing state corruption | Critical | Low-Medium | Wrong financial status or action | Decimal handling, idempotency, state machines, tests | Sprint 15 financial workflow audit | Engineering | Yes | Concurrent transition and regression tests |
| Failed backup or restore | Critical | Medium | Inability to recover production | Rollback guide and deployment backups exist | Sprint 17 restore drill | DevOps/SRE | Yes | Restore rehearsal |
| Account takeover | High | Medium | Data/control compromise | JWT auth, active/suspended checks | Security review, password/session policy review | Engineering/Security | Yes if exploitable | Auth tests and configuration audit |
| Malicious upload | High | Medium | Storage abuse, malware hosting | MIME/extension/content checks in high-risk areas | Sprint 15 upload audit across all buckets | Engineering/Security | Yes if executable upload possible | Upload tests |
| Role-only authorization bypass | High | Medium | Unauthorized management access | PropertyAssignment capability model | Sprint 15 assignment audit | Engineering | Yes | Negative persona tests |
| Admin privilege abuse or misconfiguration | High | Low-Medium | Operational/security incident | Admin-only endpoints and audit logs | Admin permission matrix and least-privilege review | Engineering/Ops | Yes if uncontrolled | Admin endpoint tests |
| Redis/Celery/outbox failure | High | Medium | Realtime/notification delays | Celery Beat and outbox architecture | Sprint 15 Redis/Celery regression and monitoring | Engineering/SRE | Usually no, unless core flows fail | Integration tests and queue monitoring |
| Shared VPS capacity limit | High | High | Production instability under launch traffic | Heavy tests avoided on shared VPS | Sprint 17 dedicated infra and Sprint 18 load tests | DevOps/SRE | Yes for broad launch | Staging capacity test |
| Fraudulent listings/providers | High | High | Trust damage | Verification/moderation systems | Sprint 19 content and moderation operations | Ops/Admin | Potentially | Moderation queue audit |
| Fake reviews | Medium | Medium | Trust damage | Booking-linked reviews | Review moderation and fraud checks | Ops/Admin | No unless widespread | Data/content audit |
| Stale listings | Medium | High | Poor customer experience | Listing statuses exist | Stale-listing operations and content audit | Product/Ops | No unless severe | Production content audit |
| Partner outage | Medium | Medium | Financing/escrow delay | Manual/partner abstraction | Escalation runbook | Ops/Partner Manager | No if disclosed | Runbook review |
| Browser/mobile regression | Medium | Low | Poor adoption | Sprint 15 installed-Chrome matrix passed at five viewports | Repeat content/device audit in Sprint 19 | Frontend/Product | Closed for Sprint 15 | Playwright browser QA report |
| Inactive inspection assignment retains private request access | High | Low | Former inspector sees private inspection data | Sprint 15 explicit access-bearing assignment statuses and regression tests | Keep status matrix in regression suite | Engineering/Security | Closed | Declined/cancelled/reassigned API tests |
| Malware uploaded in an otherwise allowed file type | Medium | Medium | Harmful document retained in private storage | Extension, MIME, size and content-signature validation | Add quarantine/scanning before risk appetite requires it | Engineering/Security | No for controlled beta if downloads remain private and disclosed | Upload security review and future scanner test |
| Visual browser/device QA unavailable during Sprint 15 run | Medium | Low | Responsive defect reaches beta | Installed-Chrome Playwright gate passed on desktop, laptop, tablet and two mobile widths | Repeat against production content in Sprint 19 | Frontend/Product | Closed for Sprint 15 | Browser QA report |
| OpenAPI enum warnings | Low | High | Client-generation friction | Warnings documented | Cleanup before generated client adoption | Engineering | No | Schema validation |
