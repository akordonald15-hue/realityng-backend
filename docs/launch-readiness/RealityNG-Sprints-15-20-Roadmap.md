# RealityNG Sprints 15-20 Roadmap

Status: scope locked for planning  
Baseline: `v2.6.0`

## Sprint 15 - Launch Readiness, Security Audit and Full Regression

Objective: prove that the complete existing platform behaves correctly and securely before infrastructure migration and public launch.

Scope:

- close the v2.6.0 full backend PostgreSQL regression follow-up;
- full frontend regression;
- Redis, Celery, Channels, realtime outbox regression;
- API security and IDOR audit;
- private document and upload security audit;
- financial workflow security review;
- WebSocket and admin authorization review;
- production configuration review;
- browser and responsive QA;
- end-to-end persona journeys;
- backup and rollback verification;
- logging and monitoring gap analysis;
- launch risk register.

Personas:

- anonymous visitor;
- buyer/tenant;
- landlord;
- agent;
- assigned agent;
- verified property manager;
- service provider;
- inspector;
- construction stakeholder/investor;
- financing applicant;
- admin.

Complexity: large.  
Risk: high because it touches every domain.  
Dependencies: current `v2.6.0` codebase, isolated PostgreSQL/Redis test environment, production-safe smoke data process.

Deliverables:

- `RealityNG-Sprint-15-Launch-Readiness-Plan.md`
- `RealityNG-Security-Audit-Checklist.md`
- `RealityNG-Persona-E2E-Test-Matrix.md`
- `RealityNG-Private-Data-Audit.md`
- `RealityNG-Launch-Risk-Register.md`
- `RealityNG-Browser-QA-Matrix.md`
- `RealityNG-v2.6.0-Regression-Closure.md`

Exit gate:

- no unresolved critical security issue;
- no high authorization issue;
- no private document leakage;
- no financial-state integrity defect;
- migrations pass;
- full regression passes;
- critical E2E journeys pass;
- backup and rollback are recoverable.

## Sprint 16 - Compliance, Legal and Trust Readiness

Objective: define the legal, privacy, marketplace, and operational rules required before public users depend on RealityNG.

Scope:

- privacy policy and data handling;
- terms and conditions;
- cookie/tracking disclosures where applicable;
- data deletion and retention policies;
- consent architecture;
- refund/cancellation policy;
- escrow and financing disclosures;
- verification, inspection, and construction disclaimers;
- marketplace/provider terms;
- fraud reporting and complaint handling;
- moderation policy;
- document retention;
- incident/breach procedure;
- NDPA/NDPR review items for professional confirmation.

Complexity: medium to large.  
Risk: high because financial and private-document wording can create legal exposure.  
Dependencies: leadership decisions, qualified Nigerian legal/privacy/financial review.

Deliverables:

- `RealityNG-Legal-and-Compliance-Readiness.md`
- `RealityNG-Data-Retention-Matrix.md`
- `RealityNG-Consent-Matrix.md`
- `RealityNG-Financial-Product-Boundaries.md`
- `RealityNG-Moderation-and-Fraud-Operations.md`
- `RealityNG-Required-Professional-Approvals.md`

Exit gate:

- high-risk capabilities have clear ownership;
- user-facing disclosures are approved;
- consent and retention classifications are defined;
- support/escalation procedures exist.

## Sprint 17 - Dedicated Production Infrastructure

Objective: move RealityNG from the shared Caretekk VPS to dedicated, cost-conscious production infrastructure with staging and a rollback path.

Scope:

- dedicated production compute;
- staging environment;
- PostgreSQL, Redis, object storage;
- Celery workers and Celery Beat;
- Daphne/ASGI and reverse proxy;
- Cloudflare, DNS, TLS, firewall;
- backups and restore;
- secrets and access control;
- CI/CD;
- observability.

Complexity: very large.  
Risk: high because migration can affect availability and data integrity.  
Dependencies: Sprint 15 risk closure, infrastructure budget, DNS/Cloudflare access, backup verification.

Deliverables:

- `RealityNG-Production-Infrastructure-Architecture.md`
- `RealityNG-Staging-Architecture.md`
- `RealityNG-Production-Migration-Runbook.md`
- `RealityNG-Backup-and-DR-Plan.md`
- `RealityNG-Observability-Plan.md`
- `RealityNG-Secrets-and-Access-Policy.md`
- `RealityNG-Storage-Classification.md`

Exit gate:

- new environment verified;
- backups confirmed;
- DNS migration planned;
- rollback path available;
- current shared environment preserved until cutover succeeds.

## Sprint 18 - Performance and Capacity Validation

Objective: determine realistic capacity and remove obvious bottlenecks before beta.

Scope:

- load test plan on staging/dedicated test infrastructure;
- workload models for homepage, search, property detail, provider listing, dashboards, financial reads/writes, messaging, WebSockets, and uploads;
- database query profiling;
- N+1 and missing-index review;
- cache review;
- capacity tiers for controlled beta and early public launch.

Complexity: large.  
Risk: medium to high because bottlenecks may require targeted fixes.  
Dependencies: Sprint 17 staging or disposable infrastructure.

Deliverables:

- `RealityNG-Load-Test-Plan.md`
- `RealityNG-Performance-Baseline.md`
- `RealityNG-Database-Performance-Audit.md`
- `RealityNG-Capacity-Model.md`
- `RealityNG-Performance-Fixes.md`

Exit gate:

- realistic staging load profile executed;
- p50/p95/p99/error-rate baseline recorded;
- high-impact query issues fixed or scheduled;
- no unacceptable capacity blocker remains.

## Sprint 19 - Production Content and UX Readiness

Objective: make production trustworthy, clear, and usable for real customers.

Scope:

- remove mock/placeholder/test content;
- audit property listings, provider profiles, walkthroughs, public media, reviews, and help pages;
- verify financial wording;
- complete support, safety, fraud, verification, inspection, construction, escrow, and financing explanations;
- browser/mobile UX pass;
- error, empty, loading, and onboarding copy review.

Complexity: medium.  
Risk: medium because misleading content can create trust and compliance problems.  
Dependencies: Sprint 16 approved language, Sprint 15 browser/UX findings.

Deliverables:

- `RealityNG-Production-Content-Audit.md`
- `RealityNG-Launch-Content-Checklist.md`
- `RealityNG-UX-Launch-Audit.md`
- `RealityNG-Production-Seed-Policy.md`
- `RealityNG-Support-and-Safety-Content.md`

Exit gate:

- no fake or misleading production content;
- launch-critical pages are complete;
- support and safety paths are visible;
- mobile and desktop launch UX approved.

## Sprint 20 - Controlled Beta Launch

Objective: launch to a controlled cohort before broad public promotion.

Scope:

- beta eligibility and onboarding;
- support process;
- issue reporting;
- incident severity;
- monitoring routine;
- analytics and feedback collection;
- fraud and financial escalation;
- daily health review;
- leadership reporting;
- rollback drill;
- public launch go/no-go.

Complexity: large.  
Risk: high because real users and live operations begin.  
Dependencies: Gates A-E green or explicitly accepted by leadership.

Deliverables:

- `RealityNG-Beta-Launch-Plan.md`
- `RealityNG-Launch-Checklist.md`
- `RealityNG-Incident-Response-Runbook.md`
- `RealityNG-Beta-Monitoring-Runbook.md`
- `RealityNG-Rollback-Drill-Report.md`
- `RealityNG-Public-Launch-Go-No-Go.md`

Exit gate:

- controlled beta cohort defined;
- monitoring active;
- rollback drill passed;
- incident and support owners assigned;
- beta go/no-go approved.

