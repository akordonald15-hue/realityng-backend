# RealityNG Jira Epics and Roadmap

Version: 1.0
Date: 2026-06-24
Planning status: CEO-aligned

## 1. Jira Structure

Recommended hierarchy:

1. Initiative: RealityNG Product Roadmap.
2. Epic: one major outcome area, normally aligned to a sprint.
3. Story: a user or operational outcome.
4. Task: implementation, migration, design, documentation, or infrastructure work.
5. Sub-task: independently assignable technical work.

Recommended project key: `RNG`

Workflow:

1. Backlog.
2. Ready for refinement.
3. Ready for sprint.
4. In progress.
5. In review.
6. QA.
7. Ready for release.
8. Done.
9. Blocked.

Required issue fields:

1. Sprint.
2. Epic link.
3. Product area.
4. Backend, frontend, data, infrastructure, design, QA, or operations label.
5. Acceptance criteria.
6. Dependency links.
7. Risk level.
8. Release note.

## 2. Completed Epics

| Epic | Name | Status | Release |
| --- | --- | --- | --- |
| RNG-EPIC-000 | Infrastructure and Architecture | Done | Sprint 0 |
| RNG-EPIC-001 | Authentication and Roles | Done | Sprint 1 |
| RNG-EPIC-002 | Property Marketplace Foundation | Done | Sprint 2 |
| RNG-EPIC-003 | Property Media and Gallery | Done | Sprint 3 |
| RNG-EPIC-035 | Branding and Design System | Done | Sprint 3.5 |
| RNG-EPIC-036 | Frontend Integration and Accessibility | Done | Sprint 3.6 |
| RNG-EPIC-004 | Favorites and Dashboard Foundations | Done | Sprint 4 |
| RNG-EPIC-DEMO | Executive Demo Mode | Done | Demo release |
| RNG-EPIC-WEB | Domain and Vercel Frontend Deployment | Done | Production frontend |

Completed epic records should link to the corresponding commits, test reports, deployment, and release notes. They must not be reopened merely because older planning documents assigned additional unbuilt scope to the same sprint number.

## 3. Active Roadmap

| Epic | Sprint | Name | Status | Primary Outcome |
| --- | --- | --- | --- | --- |
| RNG-EPIC-045 | 4.5 | CEO Alignment | Next | Restore approved flow, improve conversion and branding, add comparison and apartment sharing |
| RNG-EPIC-005 | 5 | Viewing and Rental Applications | Planned | Convert discovery into scheduled viewings and application decisions |
| RNG-EPIC-006 | 6 | Verification Layer | Planned | Establish auditable agent, CAC, and property trust signals |
| RNG-EPIC-007 | 7 | AI Assistant Foundation | Planned | Make natural-language search and guidance a primary product surface |
| RNG-EPIC-008 | 8 | Google Maps and Location Intelligence | Complete | Add spatial property discovery and privacy-safe map/list browsing |
| RNG-OPS-008A | Deferred | Google Maps Production Activation | Deferred | Activate paid Google Maps production key, populate coordinates, and complete live browser QA |
| RNG-EPIC-009 | 9 | Verified Services Marketplace | In Progress | Enable trusted property-service provider discovery, quotes, bookings, reviews, and moderation |
| RNG-EPIC-091 | 9.1 | Services Marketplace Foundation | Done | Database-backed trade categories, public provider profiles, browse APIs, and frontend services pages |
| RNG-EPIC-010 | 10 | Inspection Workflow | Planned | Request, perform, review, and release inspections |
| RNG-EPIC-011 | 11 | Construction Project Tracking | Planned | Track remote construction milestones and progress |
| RNG-EPIC-012 | 12 | Lead Management and Inquiries | Planned | Capture and manage property demand |
| RNG-EPIC-013 | 13 | Notifications and Messaging | Planned | Support workflow alerts and participant conversations |
| RNG-EPIC-014 | 14 | Payments and Transaction Tracking | Planned | Track milestones, proofs, disputes, and transaction history |
| RNG-EPIC-015 | 15 | Admin Operations and Beta Launch | Planned | Operationalize, secure, and prepare controlled beta |

## 4. Sprint 4.5 Epic Breakdown

### RNG-EPIC-045: CEO Alignment

Stories:

| Story | Summary | Acceptance Signal |
| --- | --- | --- |
| RNG-451 | Restore Base44-inspired information architecture | Approved desktop and mobile flows are connected with no orphaned primary routes |
| RNG-452 | Standardize logo visibility | Approved logo treatment is consistent on navigation, auth, and key conversion screens |
| RNG-453 | Add sign-up conversion popup | Popup is accessible, dismissible, frequency-capped, measured, and hidden for authenticated users |
| RNG-454 | Complete navigation audit | Public, authenticated, dashboard, and mobile links resolve correctly |
| RNG-455 | Remove lawyer product references | No active role selector, navigation, dashboard, marketplace, or roadmap exposes lawyer workflows |
| RNG-456 | Add comparison selection | Users can add and remove active properties with a two-to-four selection rule |
| RNG-457 | Build comparison page | Selected properties display normalized price, location, dimensions, amenities, and verification data |
| RNG-458 | Add apartment-share listing type | Authorized suppliers can create valid apartment-share listings |
| RNG-459 | Add apartment-share discovery | Users can browse, filter, and open apartment-share listings |
| RNG-460 | Update schema and regression coverage | API schema, migrations, tests, analytics, and documentation pass the definition of done |

Dependencies:

1. Approved Base44 reference or annotated screenshots.
2. Apartment-share field decision.
3. Sign-up popup trigger and analytics decision.

## 5. Sprint 5-15 Epic Summaries

### RNG-EPIC-091: Services Marketplace Foundation

Status: Done

Release branch:

- Backend: `feature/sprint-9.1-services-marketplace-foundation`
- Frontend: `feature/sprint-9.1-services-marketplace-foundation`

Stories:

| Story | Summary | Acceptance Signal |
| --- | --- | --- |
| RNG-911 | Create backend services app | `apps.services` is installed, routed, documented by OpenAPI, and covered by tests |
| RNG-912 | Model trade categories | Database-backed nested categories support active flags, display order, certification requirement, and seeded starter trades |
| RNG-913 | Model service provider public profiles | Providers link to users, support individual/company type, public profile fields, verification snapshot, status, and location display |
| RNG-914 | Model provider trades and service areas | Providers can expose multiple trades, one primary trade, skill level, experience, and service coverage areas |
| RNG-915 | Build public categories API | Guests can retrieve active trade categories without hardcoded frontend categories |
| RNG-916 | Build public providers browse API | Guests can browse active providers with search, category, state, city, LGA, provider type, ordering, and pagination |
| RNG-917 | Build public provider detail API | Guests can open provider profiles by slug without private addresses, verification documents, or internal moderation fields |
| RNG-918 | Create services marketplace page | `/services` renders hero, search, category grid, approved provider cards, loading states, and empty states |
| RNG-919 | Create provider profile page | `/services/providers/[slug]` renders public provider profile, trades, service areas, badges, biography, and future placeholders |
| RNG-920 | Add regression coverage | Backend and frontend validations pass without impacting property marketplace, verification, AI assistant, dashboards, or maps fallback |

Deferred to later Sprint 9 phases:

- Quote requests.
- Bookings.
- Reviews and ratings from completed jobs.
- Complaints and moderation workflows.
- Payments.
- Provider profile self-editing.
- Portfolio uploads.

### RNG-EPIC-005: Viewing and Rental Applications

Stories:

1. Request a viewing.
2. Accept, reject, cancel, or reschedule a viewing.
3. Submit a rental application.
4. Track applicant status.
5. Review applications as landlord or agent.
6. Audit status transitions and permissions.

### RNG-EPIC-006: Verification Layer

Stories:

1. Submit CAC evidence.
2. Submit agent verification.
3. Submit property verification.
4. Operate admin verification queues.
5. Display scoped, dated verification badges.
6. Expire or revoke verification.

### RNG-EPIC-007: AI Assistant Foundation

Stories:

1. Configure provider abstraction and privacy controls.
2. Parse natural language into validated property filters.
3. Retrieve and rank approved properties.
4. Render conversational result cards.
5. Recommend and compare properties using structured data.
6. Guide users to viewings, applications, and marketplace services.
7. Add prompt-injection, rate-limit, abuse, and cost controls.
8. Add evaluation datasets for search quality and unsupported claims.

Example acceptance queries:

1. "Show me properties in Lekki."
2. "Find land under NGN 10 million."
3. "Show me shortlets in Abuja."
4. "Compare these listings."

### RNG-EPIC-008: Google Maps and Location Intelligence

Stories:

1. Implement privacy-safe property location fields. Complete.
2. Normalize location precision and geocoding status on property records. Complete.
3. Render list, map, and split views. Complete.
4. Synchronize cards and property markers. Complete.
5. Add marker clustering foundation and graceful Google Maps fallback. Complete.
6. Add directions and nearby Places intelligence only after Google Maps production activation and data approval.
7. Track restricted Google Maps credentials, production environment variable, production coordinate audit, and live browser QA under `RNG-OPS-008A`.

### RNG-OPS-008A: Google Maps Production Activation

Status: Deferred

Reason:

Awaiting Google Cloud billing approval and production API credentials.

Dependencies:

1. Paid Google Cloud billing enabled.
2. Restricted browser API key created.
3. `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` configured in frontend production environment.
4. Production approved-listing coordinate audit completed.
5. Browser QA completed with the production Maps key.
6. Production deployment smoke test passed.

Estimate:

Small operational task, approximately 1-2 days after credentials and billing are available.

Priority:

High.

### RNG-EPIC-009: Verified Services Marketplace

Planning reference:

`docs/RealityNG-Sprint-9-Verified-Services-Marketplace-Plan.md`

Implementation stories:

1. Sprint 9.1: Marketplace foundation.
2. Sprint 9.2: Profiles, portfolio, and service areas.
3. Sprint 9.3: Quotes and booking foundation.
4. Sprint 9.4: Reviews and trust.
5. Sprint 9.5: Dashboards.
6. Sprint 9.6: Admin moderation and complaints.
7. Sprint 9.7: Testing, QA, and release hardening.

Open decisions before implementation:

1. Confirm whether MVP includes full bookings or quote requests first.
2. Confirm whether company providers are included in MVP.
3. Confirm certification requirements per service category.
4. Confirm provider contact visibility before quote request.
5. Confirm review moderation policy.

### RNG-EPIC-010: Inspection Workflow

Stories:

1. Request property, site, or construction inspection.
2. Assign an approved inspector.
3. Complete structured inspection checklist.
4. Upload evidence.
5. Review and release reports.

### RNG-EPIC-011: Construction Project Tracking

Stories:

1. Create construction projects.
2. Create and update milestones.
3. Upload progress evidence.
4. Link inspections.
5. Display project dashboards and history.

### RNG-EPIC-012: Lead Management and Inquiries

Stories:

1. Contact an agent or listing owner.
2. Protect contact details and prevent spam.
3. Manage lead stages.
4. Track response SLA.
5. Report source and conversion metrics.

### RNG-EPIC-013: Notifications and Messaging

Stories:

1. Create in-app notifications from workflow events.
2. Send email alerts.
3. Manage notification preferences and read state.
4. Create participant-scoped conversation threads.
5. Moderate abuse and observe delivery failures.

### RNG-EPIC-014: Payments and Transaction Tracking

Stories:

1. Create payment milestones.
2. Upload and review payment proof.
3. Record append-only payment events.
4. Open and manage disputes.
5. Display transaction history and non-escrow disclaimers.

### RNG-EPIC-015: Admin Operations and Beta Launch

Stories:

1. Build consolidated admin operations center.
2. Search and export permitted audit records.
3. Monitor services, jobs, providers, and queue SLAs.
4. Complete security and permission review.
5. Run end-to-end and restoration drills.
6. Prepare support, incident, moderation, and beta runbooks.
7. Complete launch sign-off.

## 6. Removed Epics

The following epics are cancelled and must not be scheduled:

| Epic | Name | Resolution |
| --- | --- | --- |
| RNG-EPIC-LEGAL | Legal Review Workflow | Removed by CEO decision |
| RNG-EPIC-LAWYER | Lawyer Marketplace and Dashboards | Removed by CEO decision |
| RNG-EPIC-LAWYER-ASSIGN | Lawyer Assignment and Opinion Flow | Removed by CEO decision |

Existing Jira issues for these areas should be resolved as `Won't Do` with a link to the CEO roadmap decision. Reusable generic document-security work may be moved to verification or inspection epics only after its scope is rewritten.

## 7. Future Roadmap

### RNG-EPIC-FUTURE-MONITORING: Remote Property Monitoring

Status: Future, unscheduled

Candidate stories:

1. Remote monitoring dashboard.
2. CCTV provider integration.
3. Smart property alerts.
4. IoT device registration and health.
5. Monitoring consent, retention, access, and incident controls.

This epic must remain outside active sprint capacity until product demand, privacy, security, hardware, and support assumptions are validated.

## 8. Dependency Order

1. Sprint 4.5 comparison and taxonomy work precedes AI comparison.
2. Sprint 4.5 apartment sharing precedes viewing and application specialization.
3. Sprint 6 verification precedes verified artisan and inspector badges.
4. Sprint 7 AI search depends on stable listing filters and approved properties.
5. Sprint 8 maps depends on normalized location data and provider credentials.
6. Sprint 10 inspections precede construction inspection integration.
7. Sprint 12 inquiry events precede full messaging automation.
8. Sprint 13 notifications precede broad payment and dispute alerts.
9. Sprint 15 beta sign-off depends on all approved beta-critical epics.

## 9. Roadmap Governance

1. Product owns epic priority and acceptance criteria.
2. Engineering owns estimates, architecture, security, and technical sequencing.
3. Design owns approved flows, responsive behavior, and accessibility specifications.
4. Operations owns queue SLAs, moderation, verification, inspection, and support readiness.
5. Any scope added to an active sprint requires an explicit tradeoff.
6. Removed and future-phase features cannot enter implementation through unlinked technical tasks.
7. Epic status must reflect shipped behavior, not document completion alone.
8. Completed work must include validation evidence and deployment or release status.
