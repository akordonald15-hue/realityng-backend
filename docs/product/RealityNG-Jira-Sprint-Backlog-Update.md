# RealityNG Jira Sprint Backlog Update

Last updated: 2026-07-28

Purpose: Provide a Jira-ready sprint and task breakdown for completed work, current stabilization, and remaining roadmap.

---

## 1. Jira Status Legend

Recommended statuses:

- Done: Implemented, validated, and no further sprint work required except regression maintenance.
- Done with Follow-up: Implemented, but a specific non-blocking follow-up should be tracked.
- In QA: Implemented and needs product/browser verification.
- Ready for Sprint Planning: Not started, scoped enough for sprint planning.
- Deferred: Approved future item, not part of next active sprint.
- Removed: Cancelled and should not be added to active roadmap.

---

## 2. Completed Epics and Sprints

### Epic: Foundation and Architecture

Sprint: Sprint 0

Status: Done

Stories:

| Story | Component | Status | Acceptance Criteria |
| --- | --- | --- | --- |
| Set up Django backend project | Backend | Done | Backend runs locally and exposes health endpoint |
| Set up Next.js frontend project | Frontend | Done | Frontend runs locally with TypeScript and Tailwind |
| Add Docker local stack | Infra | Done | Backend, frontend, Postgres, Redis, Celery, MinIO can run locally |
| Add environment examples | Backend/Frontend | Done | Required env vars documented |
| Add CI/test foundation | DevOps | Done | Lint/test workflows exist |

### Epic: Authentication and Roles

Sprint: Sprint 1

Status: Done

Stories:

| Story | Component | Status | Acceptance Criteria |
| --- | --- | --- | --- |
| User registration and login | Backend/Frontend | Done | Users can register and login |
| JWT auth flow | Backend | Done | Access/refresh behavior works |
| Role system | Backend/Frontend | Done | Buyer, landlord, agent, admin flows supported |
| Profile setup | Backend/Frontend | Done | Users can manage profile data |
| Admin approval baseline | Backend/Admin | Done | Admin can approve/reject supported requests |
| Audit log foundation | Backend | Done | Sensitive actions generate audit records |

### Epic: Property Marketplace Foundation

Sprint: Sprint 2

Status: Done

Stories:

| Story | Component | Status | Acceptance Criteria |
| --- | --- | --- | --- |
| Property model | Backend | Done | Property table and migrations exist |
| Property CRUD API | Backend | Done | Owners/admins can create/read/update/delete |
| Public approved listing API | Backend | Done | Anonymous users see approved properties only |
| Listing validation | Backend | Done | Invalid price/type/location rejected |
| Admin review workflow | Backend/Admin | Done | Admin can approve/reject listings |
| Browse properties page | Frontend | Done | Users can browse approved listings |
| Property filter panel | Frontend | Done | Supported filters send correct query params |
| Property cards | Frontend | Done | Listing summary renders correctly |

### Epic: Property Media and Gallery

Sprint: Sprint 3

Status: Done

Stories:

| Story | Component | Status | Acceptance Criteria |
| --- | --- | --- | --- |
| Property image model | Backend | Done | Images link to properties |
| Image upload API | Backend | Done | Owner/admin can upload valid images |
| Cover image workflow | Backend/Frontend | Done | Only one cover image is active |
| Gallery management UI | Frontend | Done | Owner can upload, reorder, set cover, delete |
| Public gallery serialization | Backend | Done | Public property responses include gallery data |

### Epic: Branding and Design System

Sprints: Sprint 3.5, Sprint 3.6, CEO Alignment

Status: Done with Follow-up

Stories:

| Story | Component | Status | Acceptance Criteria |
| --- | --- | --- | --- |
| RealityNG design tokens | Frontend | Done | Brand colors/type applied |
| Shared UI components | Frontend | Done | Button/Input/Card/Badge/Navbar/Footer reused |
| Homepage redesign | Frontend | Done | Hero, search, categories, featured, stats, CTA render |
| Property browse redesign | Frontend | Done | Responsive listing grid and filters render |
| Property detail redesign | Frontend | Done | Gallery, price, facts, actions, verification sections render |
| Navigation audit | Frontend | Done | Major routes are reachable |
| Mobile responsiveness | Frontend | Done | Core pages work on mobile/tablet/desktop |
| Latest logo/tagline adjustments | Frontend | In QA | Tagline sits under RealityNG wordmark and not under icon |
| AI orb brand-color update | Frontend | In QA | Assistant orb uses RealityNG emerald/gold colors |

Follow-up task:

- PM/design should visually approve latest navbar/logo and assistant orb on production after Vercel redeploy.

### Epic: Favorites and Dashboard Foundation

Sprint: Sprint 4

Status: Done

Stories:

| Story | Component | Status | Acceptance Criteria |
| --- | --- | --- | --- |
| Favorite model/API | Backend | Done | User can save one favorite per property |
| My favorites API | Backend | Done | User can list saved properties |
| `is_favorited` property flag | Backend | Done | Public property response returns correct state |
| Saved properties page | Frontend | Done | Saved property grid renders |
| Favorite button | Frontend | Done | Save/unsave works with optimistic UI |
| Dashboard quick stats/actions | Frontend | Done | Dashboard summary cards render |

### Epic: Transaction Workflow

Sprints: Sprint 5 Phase 1 to Phase 4

Status: Done

Stories:

| Story | Component | Status | Acceptance Criteria |
| --- | --- | --- | --- |
| Inquiry model and APIs | Backend | Done | User can show interest in property |
| Show Interest modal | Frontend | Done | User can submit purpose/message/contact preference |
| Owner inquiry management | Backend/Frontend | Done | Owner/agent can view and update inquiries |
| Viewing model and APIs | Backend | Done | Viewing requests link to inquiries |
| Viewing request modal | Frontend | Done | User can request physical/virtual viewing |
| Viewing owner controls | Frontend | Done | Owner/agent can confirm/reschedule/cancel/complete |
| Rental application model/APIs | Backend | Done | User can submit and track application |
| Application form | Frontend | Done | Applicant can submit required details |
| Owner application review | Frontend | Done | Owner/agent can approve/reject/manage notes |
| Unified dashboard workflow | Backend/Frontend | Done | Buyer/owner/admin see lifecycle status |
| Activity timeline foundation | Backend/Frontend | Done | Major workflow events display |

### Epic: Security Hardening

Sprint: Sprint 5.5

Status: Done

Stories:

| Story | Component | Status | Acceptance Criteria |
| --- | --- | --- | --- |
| Permission audit | Backend | Done | Object-level permissions enforced |
| Upload security review | Backend | Done | File type/size/path rules enforced |
| Demo mode boundary review | Frontend/Backend | Done | Mock mode does not leak into real mode |
| API exposure review | Backend | Done | Sensitive fields not exposed |
| CORS production fixes | Backend | Done | Browser requests from RealityNG domains succeed |

### Epic: Verification Layer

Sprint: Sprint 6

Status: Done

Stories:

| Story | Component | Status | Acceptance Criteria |
| --- | --- | --- | --- |
| Verification request model | Backend | Done | Request can be created/tracked |
| Verification document upload | Backend | Done | Documents stored privately |
| Private verification bucket | Infra/Backend | Done | Verification docs not public |
| Signed URL flow | Backend | Done | Authorized access uses expiring URLs |
| Admin verification queue | Backend/Frontend | Done | Admin can review requests |
| Approve/reject/request info | Backend/Frontend | Done | Decisions enforce permissions and audit logs |
| Verification badges | Backend/Frontend | Done | Valid badges show, expired/suspended badges do not |

### Epic: Guided Assistant Framework

Sprint: Sprint 7

Status: Done with Follow-up

Stories:

| Story | Component | Status | Acceptance Criteria |
| --- | --- | --- | --- |
| Assistant provider abstraction | Backend | Done | Supports disabled/demo/anthropic modes |
| Demo provider | Backend | Done | Deterministic supported-intent responses |
| Conversation persistence | Backend | Done | Conversations and messages are stored per user |
| Assistant config endpoint | Backend | Done | Frontend receives provider mode/label/topics |
| Dashboard assistant widget | Frontend | Done | Authenticated users can use assistant |
| Public landing assistant | Frontend | Done | Anonymous users can access walkthrough assistant |
| Premium orb visual | Frontend | In QA | Assistant uses floating RealityNG-colored orb |
| Anthropic live activation | Backend/Infra | Deferred | Requires approved API key and management signoff |

Follow-up task:

- Create separate epic/story for Anthropic production activation.

### Epic: Frontend Discovery Redesign

Sprints/Phases: Redesign Phases 1 to 7

Status: Done with QA Follow-up

Stories:

| Story | Component | Status | Acceptance Criteria |
| --- | --- | --- | --- |
| Responsive shell and task nav | Frontend | Done | Header/footer/mobile navigation work |
| Search-first homepage | Frontend | Done | Homepage prioritizes search and discovery |
| Public browsing without forced signup | Frontend | Done | Anonymous users can search and view details |
| Property card redesign | Frontend | Done | Cards show key facts and trust states |
| Property detail conversion layout | Frontend | Done | Detail page answers trust/action questions |
| Public trust/legal pages | Frontend | Done | About/safety/help/standards/legal pages exist |
| SEO/performance hardening | Frontend | Done | Metadata, sitemap, robots, build pass |
| Search tabs overflow fix | Frontend | Done | No horizontal scrollbar bar on homepage tabs |
| Public AI assistant | Frontend | Done | Assistant available from landing page without login |

---

## 3. Immediate Sprint Recommendation

## Sprint 7.5: Stabilization, QA, and PM Signoff

Status: Ready for Sprint Planning

Objective:

Confirm the latest backend/frontend production state, close visual QA issues, and prepare Sprint 8 implementation tickets.

Duration:

Small sprint or 3-5 engineering/QA days depending on PM signoff speed.

Stories:

### Story 7.5.1: Production Deployment Confirmation

Component: DevOps / Frontend

Priority: Highest

Tasks:

- Confirm Vercel production is deployed from latest frontend `main`.
- Confirm latest commit includes AI orb, tagline alignment, and Redfin-style redesign.
- Confirm Vercel env:
  - `NEXT_PUBLIC_USE_MOCKS=false`
  - `NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1`
- Confirm frontend calls real backend.

Acceptance criteria:

- `www.realityng.com` loads latest UI.
- Register/login hit `api.realityng.com`.
- No mock data appears in production real mode.

### Story 7.5.2: Browser Smoke Test

Component: QA

Priority: Highest

Tasks:

- Test register.
- Test login.
- Test logout.
- Test browse.
- Test property detail.
- Test favorite.
- Test inquiry.
- Test viewing request.
- Test rental application.
- Test verification submission.
- Test admin verification queue.
- Test public RealityNG AI.
- Test dashboard assistant.

Acceptance criteria:

- No critical workflow breaks.
- Any bugs are logged with screenshots, browser, viewport, and console/network evidence.

### Story 7.5.3: Responsive Visual QA

Component: Frontend / Design / QA

Priority: High

Tasks:

- Check desktop 1440px.
- Check laptop 1366px.
- Check tablet 768px.
- Check mobile 430px.
- Check mobile 375px.
- Verify navbar logo/tagline.
- Verify mobile logo hides tagline.
- Verify search tabs do not show scrollbar.
- Verify AI orb does not block page actions.

Acceptance criteria:

- Layout has no horizontal overflow.
- Buttons and forms remain usable.
- PM/design approves screenshots.

### Story 7.5.4: CORS and Auth Verification

Component: Backend / QA

Priority: Highest

Tasks:

- Confirm registration from `https://www.realityng.com`.
- Confirm login from `https://www.realityng.com`.
- Confirm preflight requests return correct CORS headers.
- Confirm credentialed requests work.
- Confirm unauthorized protected routes return expected responses.

Acceptance criteria:

- Browser registration/login no longer show CORS errors.
- No wildcard CORS in production.

### Story 7.5.5: PM Backlog Grooming

Component: Product / PM

Priority: Medium

Tasks:

- Mark Sprints 0-7 complete.
- Add frontend redesign phases as completed epic.
- Move Anthropic activation to deferred epic.
- Create Sprint 8 tickets.
- Validate removed lawyer/legal marketplace scope.
- Confirm next sprint priority.

Acceptance criteria:

- Jira reflects current product truth.
- Sprint 8 backlog is ready for estimation.

---

## 4. Sprint 8: Google Maps and Location Intelligence

Status: Ready for Sprint Planning

Objective:

Add map-based property discovery and location confidence.

Epic: Maps and Location Intelligence

Stories:

### Story 8.1: Map Provider Setup

Component: Infra / Frontend

Priority: High

Tasks:

- Confirm Google Maps provider decision.
- Create Google Cloud project/API key.
- Restrict API key by domain.
- Add frontend env var for map provider key.
- Document billing/quota controls.

Acceptance criteria:

- Map API loads only on approved domains.
- API key is not exposed outside expected public map usage.

### Story 8.2: Property Coordinates and Location Data

Component: Backend

Priority: High

Tasks:

- Decide exact vs approximate coordinate policy.
- Add/confirm fields for latitude/longitude or approximate location.
- Add migration if needed.
- Update property serializers.
- Add validation.

Acceptance criteria:

- Approved properties can include map-safe coordinates.
- Exact private location is not exposed unless allowed.

### Story 8.3: Browse Map View

Component: Frontend

Priority: High

Tasks:

- Add map/list toggle on `/properties`.
- Add split view on desktop.
- Add full-screen map mode on mobile.
- Add property pins.
- Sync selected pin and property card.

Acceptance criteria:

- Pins match filtered results.
- Selecting pin opens correct property preview.

### Story 8.4: Nearby Landmarks Foundation

Component: Frontend / Backend

Priority: Medium

Tasks:

- Define supported nearby categories:
  - schools
  - hospitals
  - landmarks
  - transport
- Decide API/provider data source.
- Show nearby points on property detail.

Acceptance criteria:

- Nearby information appears only when available.
- UI avoids unsupported claims.

### Story 8.5: Directions Integration

Component: Frontend

Priority: Medium

Tasks:

- Add directions link/button.
- Open Google Maps directions externally.
- Respect approximate-location policy.

Acceptance criteria:

- Directions button works for allowed properties.
- Hidden/approximate locations do not expose private exact coordinates.

### Story 8.6: Maps QA

Component: QA

Priority: High

Tasks:

- Test mobile/tablet/desktop map.
- Test filters with map pins.
- Test slow map loading.
- Test no-coordinate properties.
- Test key restriction behavior.

Acceptance criteria:

- Map does not break property browsing.
- No API key or quota issue blocks core search.

---

## 5. Sprint 9: Verified Services Marketplace

Status: Plan Ready with Open Product Decisions

Objective:

Allow users to discover, evaluate, request quotes from, book, and review verified property-related service providers.

Planning reference:

`docs/RealityNG-Sprint-9-Verified-Services-Marketplace-Plan.md`

Stories:

| Story | Component | Priority | Notes |
| --- | --- | --- | --- |
| Sprint 9.1 Marketplace foundation | Backend/Frontend | High | Services app, category model, provider model, public browse shell |
| Sprint 9.2 Profiles, portfolio, and service areas | Backend/Frontend | High | Provider profile editor, portfolio uploads, area coverage |
| Sprint 9.3 Quotes and booking foundation | Backend/Frontend | High | QuoteRequest, Quote, Booking workflows |
| Sprint 9.4 Reviews and trust | Backend/Frontend | Medium | Booking-only reviews, ratings, provider responses |
| Sprint 9.5 Dashboards | Backend/Frontend | Medium | Customer, provider, and admin operational dashboards |
| Sprint 9.6 Admin moderation and complaints | Backend/Admin | Medium | Provider suspension, complaints, review moderation |
| Sprint 9.7 Testing and release hardening | QA/Engineering | High | Full regression, security, browser QA, release report |

Acceptance criteria:

- Users can browse approved service providers by category and location.
- Verified providers show clear, scoped, non-misleading badges.
- Users can request quotes and manage booking status where approved.
- Reviews can only be left for eligible completed bookings.
- Admins can moderate providers, complaints, and suspicious reviews.
- Existing property, verification, assistant, and map workflows are not regressed.

Open product decisions:

- Quote-only MVP versus quote plus booking MVP.
- Individual artisans only versus individual plus company providers.
- Mandatory certification categories.
- Contact visibility before quote request.
- Review auto-publish versus moderation-first.

---

## 6. Sprint 10: Inspection Workflow

Status: Ready for Product Scoping

Objective:

Support property/site/construction inspection requests and reports.

Stories:

| Story | Component | Priority |
| --- | --- | --- |
| Inspection request model | Backend | High |
| Inspection request frontend | Frontend | High |P
| Admin assignment workflow | Admin | High |
| Inspector report upload | Backend/Frontend | High |
| Evidence management | Backend/Frontend | High |
| Inspection status tracking | Backend/Frontend | Medium |

Acceptance criteria:

- User can request inspection.
- Admin can manage request.
- Inspector/admin can upload report.
- Authorized user can view report.

---

## 7. Sprint 11: Construction Project Tracking

Status: Planned

Objective:

Give property owners/diaspora investors visibility into construction progress.

Stories:

| Story | Component | Priority |
| --- | --- | --- |
| Construction project model | Backend | High |
| Milestone model and API | Backend | High |
| Progress update uploads | Backend/Frontend | High |
| Owner project dashboard | Frontend | High |
| Link inspections to milestones | Backend/Frontend | Medium |
| Project activity timeline | Frontend | Medium |

Acceptance criteria:

- Projects have milestones.
- Milestones track progress/evidence.
- Owners can view progress remotely.

---

## 8. Sprint 12: Lead Management and Inquiries Expansion

Status: Planned

Objective:

Improve owner/agent pipeline management.

Stories:

| Story | Component | Priority |
| --- | --- | --- |
| Lead inbox | Backend/Frontend | High |
| Lead pipeline stages | Backend/Frontend | High |
| Agent assignment | Backend/Admin | Medium |
| Follow-up tracking | Backend/Frontend | Medium |
| Conversion analytics | Backend/Frontend | Medium |
| Contact-agent workflow | Backend/Frontend | High |

Acceptance criteria:

- Agents can manage leads.
- Leads are connected to properties/users.
- Conversion metrics are visible.

---

## 9. Sprint 13: Notifications and Messaging

Status: Planned

Objective:

Turn existing event hooks into user-facing notifications and messaging.

Stories:

| Story | Component | Priority |
| --- | --- | --- |
| Notification model/API | Backend | High |
| Notification center UI | Frontend | High |
| Email provider setup | Infra/Backend | High |
| Notification preferences | Backend/Frontend | Medium |
| Messaging thread model | Backend | High |
| Messaging UI | Frontend | High |
| Read/unread state | Backend/Frontend | Medium |

Acceptance criteria:

- Users receive notifications for key workflow events.
- Users can manage read/unread notifications.
- Messaging is permission-scoped.

---

## 10. Sprint 14: Payments and Transaction Tracking

Status: Planned

Objective:

Track transaction milestones and payment proofs.

Stories:

| Story | Component | Priority |
| --- | --- | --- |
| Payment milestone model | Backend | High |
| Payment proof upload | Backend/Frontend | High |
| Transaction history UI | Frontend | High |
| Dispute workflow | Backend/Frontend | Medium |
| Admin transaction review | Admin | Medium |
| Payment provider research | Product/Engineering | High |

Acceptance criteria:

- Users can track milestones.
- Proofs are securely uploaded.
- Disputes preserve evidence/history.
- UI does not imply escrow/custody unless legally approved.

---

## 11. Sprint 15: Admin Operations and Beta Launch

Status: Planned

Objective:

Prepare RealityNG for controlled beta operations.

Stories:

| Story | Component | Priority |
| --- | --- | --- |
| Admin operations dashboard | Admin | High |
| Audit log search | Backend/Admin | High |
| Monitoring and alerting | Infra | High |
| Security readiness review | Security | High |
| Backup/restore drill | Infra | High |
| Production runbook | DevOps | High |
| Beta launch checklist | PM/QA | High |
| Support workflow | Operations | Medium |

Acceptance criteria:

- Admin can monitor queues and audit events.
- Critical systems have health visibility.
- Beta checklist is signed off.
- Rollback and incident process is documented.

---

## 12. Deferred Epics

### Anthropic Production Activation

Status: Deferred pending management approval

Tasks:

- Securely provision Anthropic API key.
- Set backend `AI_PROVIDER_MODE=anthropic`.
- Validate provider-backed response.
- Validate AI search.
- Validate AI comparison.
- Validate token logging and cost monitoring.
- Validate provider outage fallback.
- Confirm no prompts/secrets leak.

Acceptance criteria:

- Live provider works.
- Demo mode remains available as fallback.
- Cost and safety controls are approved.

### Cloudflare Full Strict Origin Security

Status: Deferred production hardening

Tasks:

- Add origin TLS certificate.
- Enable origin HTTPS on port 443.
- Switch Cloudflare SSL from Flexible to Full Strict.
- Enable HSTS only after Full Strict is stable.

Acceptance criteria:

- Browser to Cloudflare and Cloudflare to origin are both encrypted.
- No redirect loops.
- API remains healthy.

### Remote Property Monitoring

Status: Future phase

Tasks:

- CCTV integration.
- Smart property monitoring.
- IoT integration.
- Remote monitoring dashboard.

Acceptance criteria:

- Only start after privacy, vendor, hardware, and support policies are approved.

---

## 13. Removed Scope

Status: Removed

Do not create active Jira tickets for:

- Lawyer marketplace.
- Lawyer dashboard.
- Lawyer assignment.
- Legal review workflow.

---

## 14. PM Immediate Actions

1. Close completed sprint tickets from Sprint 0 through Sprint 7.
2. Create a completed epic for Frontend Discovery Redesign Phases 1-7.
3. Create Sprint 7.5 Stabilization and QA sprint.
4. Add Sprint 8 Maps and Location Intelligence tickets.
5. Move Anthropic live provider to Deferred.
6. Keep lawyer/legal marketplace features Removed.
7. Schedule product/design signoff for latest homepage, navbar, AI orb, browse, detail, and verification flows.
