# RealityNG Public Launch Master Plan

Status: planning locked  
Baseline release: `v2.6.0`  
Backend baseline: `161a741e7d9e4999e7a23ae9d6881a55928d5a43`  
Frontend baseline: `db409f06d3b0878d22f41ead537cd9cba3e0d5e4`

## Purpose

RealityNG has completed the major product-building phase. Sprints 15-20 move the product from feature-complete engineering into controlled public launch readiness.

Default policy from this point:

- no large new product features before public beta;
- classify discovered work as launch blocker or post-launch backlog;
- test production behavior on staging/dedicated infrastructure, not the shared Caretekk VPS;
- preserve RealityNG's marketplace/orchestration role, especially around escrow and financing.

## Current Platform Baseline

| Area | Status | Notes |
| --- | --- | --- |
| Authentication and identity | Complete | Registration, login/logout, JWT, roles, suspended users, role requests, profile endpoints. |
| Authorization | Complete, requires launch audit | Object ownership, admin-only endpoints, property assignment capabilities, private serializers. |
| Property marketplace | Complete | Listings, search, details, media, favorites, inquiries, viewings, applications, leads, transaction center. |
| Verification | Complete | User/property verification, private documents, signed URLs, admin review, public-safe verification display. |
| Maps/location | Partial/deferred activation | Engineering foundation exists; production Google Maps activation remains operationally deferred. |
| AI assistant | Complete in configured mode | Public assistant and backend-controlled provider mode. |
| Services marketplace | Complete | Provider profiles, portfolios, service areas, quote requests, bookings foundation, reviews, complaints, appeals. |
| Inspections | Complete | Inspection requests, assignment, reports, evidence, walkthroughs, private media and moderation. |
| Construction | Complete | Projects, stakeholders, milestones, weighted progress, evidence, inspection linkage, dashboards. |
| Communications | Complete | Notifications, preferences, messaging, WebSockets, Redis Channels, Celery, Beat, outbox, throttling. |
| Financial domain | Complete as software, gated operationally | Transactions, payment proofs, disputes, escrow architecture, financing applications, consent, documents, offers. |
| Admin operations | Complete, requires launch audit | Moderation and operations across properties, services, inspections, construction, payments, financing. |

## Known v2.6.0 Follow-Up

The v2.6.0 release passed financial-domain tests, migrations, production smoke testing, frontend regression, realtime smoke, and health checks. The final post-merge full backend PostgreSQL suite timed out locally before completion. Earlier pre-merge PostgreSQL validation reached `361 passed`.

Sprint 15 must close this item in a stable environment before launch readiness can be marked green.

## Financial Product Boundary

RealityNG software supports escrow and financing workflows, but RealityNG must not present itself as a bank, lender, mortgage bank, underwriter, credit bureau, insurer, escrow custodian, investment company, or legal adviser unless leadership separately approves the legal/regulatory model.

Escrow real-money activation requires:

- approved custody/financial partner;
- legal review and commercial agreement;
- sandbox/API validation;
- webhook security validation;
- reconciliation, settlement, dispute, and fee procedures;
- named operational owner.

Financing real-partner activation requires:

- licensed financing/rent-finance/mortgage partner;
- approved product terms;
- applicant consent and privacy/data-sharing agreement;
- partner-owned underwriting and funding decisions;
- funding confirmation process;
- legal/compliance approval.

## Launch Readiness Assessment

| Dimension | Current assessment |
| --- | --- |
| Software | Strong feature coverage, but Sprint 15 must complete stable full regression. |
| Security | Security controls exist, but launch requires adversarial IDOR, upload, document, financial, and admin audits. |
| Compliance | Not launch-ready until legal/privacy/financial disclosures are professionally reviewed. |
| Infrastructure | Current shared VPS is acceptable for development, not broad public launch. |
| Performance | Not proven under realistic beta traffic on dedicated/staging infrastructure. |
| Content/UX | Needs production content audit, placeholder removal, support copy, and browser/mobile QA. |
| Operations | Needs incident response, support process, monitoring ownership, rollback rehearsal, and beta runbook. |

## Sprint Sequence

1. Sprint 15 - Launch Readiness, Security Audit and Full Regression
2. Sprint 16 - Compliance, Legal and Trust Readiness
3. Sprint 17 - Dedicated Production Infrastructure
4. Sprint 18 - Performance and Capacity Validation
5. Sprint 19 - Production Content and UX Readiness
6. Sprint 20 - Controlled Beta Launch

The sequence is locked unless a concrete dependency requires adjustment.

## Parallel Work

Some Sprint 16 legal/compliance review may begin while Sprint 15 engineering audit runs. Infrastructure planning for Sprint 17 can also begin in discovery mode, but environment migration should wait until Sprint 15 has identified critical technical risks.

## Reused Authoritative Documents

Use these existing documents as source material:

- `docs/RealityNG-Sprint-14-Financial-Threat-Model.md`
- `docs/RealityNG-Sprint-14.1-Escrow-Implementation-Report.md`
- `docs/RealityNG-Sprint-14.2-Property-Financing-Implementation-Report.md`
- `docs/RealityNG-Sprint-14.2-Security-and-Integration-Review.md`
- `docs/RealityNG-Messaging-Reliability-Architecture.md`
- `docs/RealityNG-Realtime-Outbox-Design.md`
- `docs/RealityNG-Inspection-Architecture.md`
- `docs/RealityNG-Sprint-11-Construction-Tracking-Report.md`
- `docs/RealityNG-Rollback-Guide.md`
- `docs/RealityNG-Staging-Load-Test-Plan.md`

## Recommendation

Proceed to Sprint 15. Do not add new marketplace or financial features until launch readiness gates have a clear status.

