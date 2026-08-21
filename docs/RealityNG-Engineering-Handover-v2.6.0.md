# RealityNG Engineering Handover - v2.6.0

Status: active handover  
Audience: incoming engineer, project manager, technical lead  
Release baseline: `v2.6.0`  
Backend repository: `https://github.com/akordonald15-hue/realityng-backend`  
Frontend repository: `https://github.com/akordonald15-hue/realityng-frontend`

## 1. Executive Summary

RealityNG is a Nigerian, trust-first PropTech marketplace for property discovery, verification, services, inspection, construction tracking, messaging, transactions, escrow orchestration, and financing partner workflows.

The product has moved through the major product-building phase and is now at release `v2.6.0`. From this point onward, the recommended engineering posture is launch readiness rather than feature expansion. The next planned sprint is Sprint 15: launch readiness, security audit, and full regression.

Do not begin new product features until Sprints 15-20 launch gates are agreed and tracked.

## 2. Current Git Baseline

### Backend

- Main commit: `161a741e7d9e4999e7a23ae9d6881a55928d5a43`
- Release tag: `v2.6.0`
- Release content: Sprint 14.1 escrow plus Sprint 14.2 property financing
- Planning branch: `planning/public-launch-readiness`
- Latest planning commit at handover time: `48bbbb65ebc8d6d6ad34d94c8d456429580feba3` before this handover update

### Frontend

- Main commit: `db409f06d3b0878d22f41ead537cd9cba3e0d5e4`
- Release tag: `v2.6.0`
- Release content: transaction, escrow, and financing UI

## 3. Production Baseline

Known production endpoints:

- Frontend: `https://www.realityng.com`
- Backend API: `https://api.realityng.com/api/v1`
- Backend health: `https://api.realityng.com/api/v1/health/`

RealityNG currently shares a lean VPS with Caretekk. Treat this as a development/controlled-production environment, not a broad public launch environment.

Safety rules:

- do not run heavy load tests against the shared VPS;
- do not restart Caretekk containers;
- do not prune Docker;
- do not delete shared volumes;
- do not touch shared Nginx unless a narrowly scoped RealityNG routing issue requires it;
- create backups before production migrations or deployments.

## 4. What Has Been Built

### Authentication and Identity

- User registration, login, logout, refresh token, password reset.
- JWT authentication with token blacklist.
- Roles, role requests, admin role approval/rejection.
- User profiles, active/suspended user handling.
- Audit log foundation.

### Property Marketplace

- Property listing CRUD.
- Public property browse and detail pages.
- Search/filtering.
- Property media and gallery management.
- Favorites/saved properties.
- Inquiries/show interest.
- Viewing requests.
- Rental applications.
- Lead management pipeline on existing inquiries.
- Dashboard summaries and activity.
- Transaction center and transaction milestones.

### Property Assignment

- Explicit `PropertyAssignment` / managed-property relationship.
- Capability-based property management.
- Role alone must not authorize access to another property.
- Used to protect walkthrough, inspection, construction, and lead workflows.

### Verification

- User verification.
- Property verification.
- Private verification documents.
- Signed URL access.
- Admin verification queues and moderation.
- Public-safe verification display.

### AI Assistant

- Backend-controlled assistant provider mode.
- Demo provider mode is production-safe when configured.
- Anthropic provider code preserved but only active when server env enables it.
- Public assistant widget and dashboard assistant surfaces.

Production-safe demo configuration:

```env
AI_ASSISTANT_ENABLED=true
AI_PROVIDER_MODE=demo
```

### Maps and Location Intelligence

- Location fields on property model.
- Public-safe approximate coordinate exposure.
- Map/list/split view frontend foundation.
- Google Maps production activation is deferred until billing, restricted key, coordinate population, and browser QA are complete.

### Services Marketplace

- Trade categories.
- Public provider browse and provider detail.
- Provider profile lifecycle.
- Provider trades.
- Service areas.
- Portfolio image management.
- Quote requests.
- Minimal service booking foundation.
- Booking-linked reviews and rating aggregates.
- Provider responses.
- Review flagging.
- Complaints and complaint evidence.
- Provider warnings, suspension, reactivation, and appeals.
- Admin moderation and operational dashboards.

### Inspection and Walkthroughs

- Inspection requests.
- Inspector assignment.
- Inspection reports.
- Inspection evidence.
- Private inspection storage.
- Property walkthrough uploads.
- Walkthrough moderation.
- Owner/assigned-agent/verified-manager/admin authorization model.

### Construction Tracking

- Construction projects.
- Project stakeholders.
- Project milestones.
- Weighted progress calculation.
- Progress updates.
- Construction evidence.
- Inspection-to-milestone linkage.
- Owner/investor/project-ops/admin dashboards.

### Communications

- Notifications.
- Notification preferences.
- Messaging threads.
- WebSocket support through ASGI/Daphne.
- Redis-backed Channels.
- Celery and Celery Beat.
- Realtime outbox.
- Message idempotency.
- Reconnect synchronization.
- WebSocket throttling.

### Payments, Escrow, and Financing

- Transaction tracking.
- Payment milestones.
- Payment proof upload and private signed access.
- Disputes.
- Escrow provider abstraction.
- Escrow funding events.
- Release/refund workflows.
- Reconciliation.
- Webhook idempotency and signature handling.
- Financing partners and products.
- Financing applications.
- Financing consent.
- Private financing documents.
- Partner submissions.
- Partner offers.
- Offer acceptance/decline.
- Funding state tracking.
- Admin finance operations.

Important product boundary:

RealityNG is not currently a bank, lender, mortgage bank, underwriter, credit bureau, escrow custodian, loan collector, insurer, investment company, or legal adviser. The software records and orchestrates partner-owned decisions and partner-confirmed financial states.

## 5. Release History

| Release | Summary |
| --- | --- |
| `v2.0.0` | Verification and guided assistant release. |
| `v2.1.0` | Services marketplace release baseline. |
| `v2.2.0` | Inspection and walkthrough baseline. |
| `v2.3.0` | Construction tracking baseline. |
| `v2.4.0` | Lead management baseline. |
| `v2.5.0` | Notifications, messaging, ASGI/realtime baseline. |
| `v2.6.0` | Financial domain release: escrow plus property financing. |

## 6. v2.6.0 Validation Summary

Passed before/around release:

- backend lint;
- Django check;
- migration check;
- OpenAPI validation with no errors and known enum warnings;
- PostgreSQL financing tests;
- PostgreSQL payments tests;
- frontend lint;
- frontend typecheck;
- frontend tests;
- mock frontend build;
- real API frontend build;
- production migrations;
- production smoke test;
- realtime outbox smoke;
- live WebSocket handshake;
- RealityNG health check;
- Caretekk health check.

Known validation follow-up:

- The final post-merge full backend PostgreSQL suite timed out locally after release. Earlier pre-merge PostgreSQL validation reached `361 passed`.
- Sprint 15 must rerun the full backend PostgreSQL suite in a stable CI/staging environment and record the result.

## 7. Current Documentation Map

### Current authoritative launch docs

- `docs/launch-readiness/RealityNG-Public-Launch-Master-Plan.md`
- `docs/launch-readiness/RealityNG-Sprints-15-20-Roadmap.md`
- `docs/launch-readiness/RealityNG-Launch-Dependency-Map.md`
- `docs/launch-readiness/RealityNG-Launch-Gates.md`
- `docs/launch-readiness/RealityNG-Launch-Risk-Register.md`
- `docs/launch-readiness/RealityNG-Global-Definition-of-Done.md`
- `docs/launch-readiness/RealityNG-Environment-Strategy.md`
- `docs/launch-readiness/RealityNG-Launch-Blocker-Policy.md`

### Product/PRD documents mirrored from the workspace

These are stored in `docs/product/` so they can be pulled from GitHub:

- `RealityNG-PRD.md`
- `RealityNG-Sprint-Breakdown.md`
- `RealityNG-Jira-Epics-and-Roadmap.md`
- `RealityNG-Jira-Sprint-Backlog-Update.md`
- `RealityNG-System-Design-Document.md`
- `RealityNG-ERD-Specification.md`
- `RealityNG-API-Specification.md`
- `RealityNG-UI-UX-Flows.md`
- `RealityNG-UIUX-Designer-Brief.md`
- `RealityNG-Fullstack-Engineer-Handoff-Legacy.md`
- `RealityNG-Project-Status-and-PM-Handoff.md`
- `realityng-sprint-checklist-for-jira.md`

Note: some older product documents still contain earlier sprint labels and should be read as historical/product background unless superseded by the v2.6.0 launch-readiness docs.

## 8. Local Setup on a New PC

### Clone repositories

```powershell
mkdir C:\Users\<you>\Downloads\Realityng
cd C:\Users\<you>\Downloads\Realityng
git clone https://github.com/akordonald15-hue/realityng-backend.git backend
git clone https://github.com/akordonald15-hue/realityng-frontend.git frontend
```

### Backend setup

```powershell
cd backend
git checkout main
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements\dev.txt
Copy-Item .env.example .env
docker compose up --build
```

Useful checks:

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py spectacular --validate --file schema.yml
.\.venv\Scripts\pytest.exe -q
```

If running outside Docker, do not accidentally fall back to SQLite when validating PostgreSQL behavior. Use a real PostgreSQL connection for migration/security/regression gates.

### Frontend setup

```powershell
cd frontend
git checkout main
npm install
Copy-Item .env.example .env.local
npm run dev
```

Production-like local frontend env:

```env
NEXT_PUBLIC_USE_MOCKS=false
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=
```

Useful checks:

```powershell
npm run lint
npm run typecheck
npm run test
$env:NEXT_PUBLIC_USE_MOCKS="true"; npm run build
$env:NEXT_PUBLIC_USE_MOCKS="false"; $env:NEXT_PUBLIC_API_BASE_URL="https://api.realityng.com/api/v1"; npm run build
```

## 9. Important Environment Notes

Backend:

- `DATABASE_URL`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `CHANNEL_LAYER_REDIS_URL`
- `MINIO_ENDPOINT`
- `MINIO_PUBLIC_ENDPOINT`
- `MINIO_ACCESS_KEY`
- `MINIO_SECRET_KEY`
- `AI_ASSISTANT_ENABLED`
- `AI_PROVIDER_MODE`
- `ANTHROPIC_API_KEY`
- `PAYMENT_PROOF_BUCKET_NAME`
- `FINANCING_DOCUMENT_BUCKET_NAME`
- `FINANCING_CONSENT_TERMS_VERSION`

Frontend:

- `NEXT_PUBLIC_USE_MOCKS`
- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`
- `NEXT_PUBLIC_SENTRY_DSN`
- `NEXT_PUBLIC_SENTRY_ENVIRONMENT`

Secrets must not be committed. Production `.env` values should be transferred through a secure channel or secret manager, not through GitHub.

## 10. What Remains Before Public Launch

RealityNG is not yet broad-public-launch-ready. The product is feature-rich, but launch work remains.

### Sprint 15 - Launch Readiness, Security Audit and Full Regression

- close full backend PostgreSQL regression follow-up;
- full frontend regression;
- Redis/Celery/Channels regression;
- IDOR and authorization audit;
- private document audit;
- upload security audit;
- financial workflow security audit;
- WebSocket security;
- admin authorization;
- browser/mobile QA;
- persona E2E matrix;
- backup/rollback verification;
- logging/monitoring gap analysis.

### Sprint 16 - Compliance, Legal and Trust Readiness

- privacy policy;
- terms;
- data retention/deletion;
- consent matrix;
- escrow/financing disclosures;
- verification/inspection/construction disclaimers;
- moderation/fraud policies;
- qualified legal/privacy/financial review.

### Sprint 17 - Dedicated Production Infrastructure

- move RealityNG away from shared Caretekk VPS before serious public traffic;
- staging environment;
- dedicated production compute;
- PostgreSQL/Redis/object storage sizing;
- backups/restore;
- Cloudflare/DNS/TLS;
- monitoring;
- CI/CD and secrets/access policy.

### Sprint 18 - Performance and Capacity Validation

- load testing on staging, not production;
- database query profiling;
- N+1 review;
- cache review;
- WebSocket and upload capacity;
- capacity model for controlled beta.

### Sprint 19 - Production Content and UX Readiness

- remove fake/mock/placeholder public content;
- review real listings and provider profiles;
- confirm public walkthrough/media quality and privacy;
- verify financial wording;
- help/safety/support content;
- browser/mobile UX launch audit.

### Sprint 20 - Controlled Beta Launch

- define beta cohort;
- support and incident processes;
- monitoring routine;
- rollback drill;
- leadership reporting;
- public launch go/no-go.

## 11. Known Launch Risks

Highest-priority risks:

- full backend PostgreSQL regression not yet closed after v2.6.0;
- private document leakage;
- IDOR or role-only authorization mistake;
- financial wording implying regulated responsibilities RealityNG does not hold;
- shared VPS capacity;
- backup/restore not rehearsed;
- insufficient legal/privacy approval;
- insufficient staging load testing;
- production content or fake data weakening trust.

Use `docs/launch-readiness/RealityNG-Launch-Risk-Register.md` as the active register.

## 12. Branching Recommendation

Use launch-focused branch names:

- `audit/sprint-15-launch-readiness`
- `compliance/sprint-16-legal-trust-readiness`
- `infra/sprint-17-dedicated-production`
- `perf/sprint-18-capacity-validation`
- `content/sprint-19-production-ux-readiness`
- `release/sprint-20-controlled-beta`

Avoid starting Sprint 15 on stale feature branches. Branch from latest `origin/main`.

## 13. Immediate Next Action

Start Sprint 15 only after this handover is pulled on the new PC.

Recommended Sprint 15 first task:

1. Provision stable isolated PostgreSQL and Redis test stack.
2. Confirm backend uses PostgreSQL, not SQLite.
3. Run full backend suite to close the v2.6.0 timeout follow-up.
4. Run frontend regression.
5. Start the persona and IDOR audit matrix.

## 14. Final Handover Verdict

RealityNG is stable at `v2.6.0` and ready to enter launch-readiness work. It is not yet ready for broad public launch until Sprints 15-20 gates are satisfied.

