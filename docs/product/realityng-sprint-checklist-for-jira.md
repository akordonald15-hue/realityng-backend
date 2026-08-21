# RealityNG Sprint Checklist for Jira

Last updated: 2026-07-28

Use this file as the quick Jira checklist. For detailed context, see:

- `RealityNG-Project-Status-and-PM-Handoff.md`
- `RealityNG-Jira-Sprint-Backlog-Update.md`

---

## Current State

RealityNG has completed the core marketplace platform through Sprint 7, released `v2.0.0`, deployed the backend and frontend from `main`, and completed additional frontend redesign/branding refinements after the v2 release.

Current stage:

- Sprints 0-7: Complete
- v2.0.0: Released
- Backend: Real API deployed
- Frontend: Vercel production frontend deployed
- AI assistant: Guided demo mode active
- Anthropic live provider: Deferred pending management approval
- Next recommended sprint: Sprint 7.5 Stabilization and PM Signoff
- Next major product sprint: Sprint 8 Google Maps and Location Intelligence

Latest known commits:

- Backend main: `f6f29ab0219700b9f1b1c4544d3b17a8db1f3365`
- Frontend main: `e6f836f85e9a06bcafde3f3985093513ac4f724c`

Production:

- Frontend: `https://www.realityng.com`
- Backend API: `https://api.realityng.com/api/v1`
- Health: `https://api.realityng.com/api/v1/health/`

---

## Completed Sprints

### Sprint 0: Infrastructure and Architecture

Status: Done

Checklist:

- [x] Django backend foundation
- [x] Next.js frontend foundation
- [x] PostgreSQL
- [x] Redis
- [x] Celery
- [x] MinIO
- [x] Docker and Docker Compose
- [x] Split Django settings
- [x] Environment variable strategy
- [x] Health endpoint
- [x] DRF and OpenAPI foundation
- [x] Logging foundation
- [x] Base model conventions
- [x] Test foundation
- [x] CI/CD foundation

Jira action: Close sprint as Done.

### Sprint 1: Authentication, Roles, Profiles, Admin Approval

Status: Done

Checklist:

- [x] Registration
- [x] Login
- [x] JWT authentication
- [x] Logout/refresh foundation
- [x] User roles
- [x] User profiles
- [x] Admin approval baseline
- [x] Audit log foundation
- [x] Frontend auth pages
- [x] Role onboarding
- [x] Protected routes

Jira action: Close sprint as Done.

### Sprint 2: Property Marketplace Foundation

Status: Done

Checklist:

- [x] Property model
- [x] Property CRUD APIs
- [x] Draft listings
- [x] Owner/admin permissions
- [x] Soft delete
- [x] Validation
- [x] Admin review workflow
- [x] Public approved listing endpoint
- [x] Search/filter/order/pagination
- [x] Browse page
- [x] Filter panel
- [x] Property cards
- [x] Listing creation baseline

Jira action: Close sprint as Done.

### Sprint 3: Property Media and Gallery

Status: Done

Checklist:

- [x] Property image model
- [x] Upload/list/update/delete APIs
- [x] Cover image workflow
- [x] One-cover enforcement
- [x] File type validation
- [x] File size validation
- [x] Image count validation
- [x] MinIO integration
- [x] Public cover/gallery serialization
- [x] Frontend uploader
- [x] Gallery management

Jira action: Close sprint as Done.

### Sprint 3.5: Branding and Design System

Status: Done

Checklist:

- [x] RealityNG design system
- [x] Brand colors
- [x] Typography
- [x] Shared UI components
- [x] Navbar
- [x] Footer
- [x] Homepage redesign
- [x] Browse redesign
- [x] Property detail redesign
- [x] Responsive improvements
- [x] Accessibility pass
- [x] Logo/icon/favicon/splash updates

Jira action: Close sprint as Done.

### Sprint 3.6: Frontend Integration and Accessibility Audit

Status: Done

Checklist:

- [x] Route audit
- [x] Navigation audit
- [x] Mobile navigation audit
- [x] Footer audit
- [x] Dashboard navigation audit
- [x] Responsive fixes
- [x] Shared component consistency
- [x] Loading states
- [x] Empty states
- [x] Property flow audit

Jira action: Close sprint as Done.

### Sprint 4: Favorites and Dashboard Foundations

Status: Done

Checklist:

- [x] Favorite model
- [x] Unique favorite constraint
- [x] Save favorite API
- [x] Remove favorite API
- [x] My favorites API
- [x] `is_favorited` in property response
- [x] Saved properties page
- [x] Favorite buttons
- [x] Optimistic UI
- [x] Dashboard quick stats
- [x] Dashboard quick actions
- [x] Audit events

Jira action: Close sprint as Done.

### Demo Mode and Executive Showcase

Status: Done

Checklist:

- [x] `NEXT_PUBLIC_USE_MOCKS` switch
- [x] Mock authentication
- [x] Mock users
- [x] Mock properties
- [x] Mock inquiries
- [x] Mock analytics
- [x] Mock dashboards
- [x] Backend-independent frontend demo
- [x] Demo credentials removed from auth UI

Jira action: Close as completed support epic.

### Sprint 4.5: CEO Alignment and Prototype Restoration

Status: Done

Checklist:

- [x] Base44-style flow alignment
- [x] Larger logo treatment
- [x] Official slogan
- [x] Sign-up conversion modal
- [x] Role selection modal
- [x] Protected action wrapper
- [x] Post-login return flow
- [x] Apartment-share foundation
- [x] Property comparison foundation
- [x] Lawyer/legal marketplace references removed
- [x] Artisans section added
- [x] Show Interest button added

Jira action: Close sprint as Done.

### Sprint 5 Phase 1: Inquiry / Show Interest

Status: Done

Checklist:

- [x] Inquiry model
- [x] Inquiry status pipeline
- [x] Create inquiry API
- [x] My inquiries API
- [x] Received inquiries API
- [x] Retrieve/update status APIs
- [x] Internal notes
- [x] Object-level permissions
- [x] Show Interest modal
- [x] Buyer dashboard section
- [x] Owner/agent management
- [x] Demo mode support
- [x] Audit events

Jira action: Close phase as Done.

### Sprint 5 Phase 2: Viewing Requests

Status: Done

Checklist:

- [x] Viewing model linked to inquiry
- [x] Requested/confirmed/rescheduled/cancelled/completed workflow
- [x] Create viewing API
- [x] My viewings API
- [x] Received viewings API
- [x] Confirm/reschedule/cancel/complete APIs
- [x] Viewing request modal
- [x] Buyer dashboard viewings
- [x] Owner/agent management
- [x] Scheduling foundation
- [x] Demo mode support
- [x] Audit events

Jira action: Close phase as Done.

### Sprint 5 Phase 3: Rental Applications

Status: Done

Checklist:

- [x] Rental application model
- [x] Submit application API
- [x] My applications API
- [x] Received applications API
- [x] Retrieve application API
- [x] Status transitions
- [x] Owner notes
- [x] Application form
- [x] Buyer dashboard applications
- [x] Owner/agent review controls
- [x] Demo mode support
- [x] Audit events

Jira action: Close phase as Done.

### Sprint 5 Phase 4: Workflow Integration and Dashboards

Status: Done

Checklist:

- [x] Unified transaction lifecycle
- [x] Buyer transaction center
- [x] Landlord dashboard improvements
- [x] Agent dashboard improvements
- [x] Admin dashboard improvements
- [x] Activity timeline foundation
- [x] Workflow entity linking
- [x] Status badges
- [x] Notification center placeholder

Jira action: Close phase as Done.

### Sprint 5.5: Security Audit and Hardening

Status: Done

Checklist:

- [x] Auth security review
- [x] Object permission review
- [x] Admin permission review
- [x] API exposure review
- [x] Upload security review
- [x] Demo mode boundary review
- [x] CORS/CSRF review
- [x] Docker/infrastructure review
- [x] Security tests

Jira action: Close sprint as Done.

### Sprint 6: Verification Layer

Status: Done

Checklist:

- [x] Verification request model
- [x] Property verification workflow
- [x] Verification document model
- [x] Private verification storage
- [x] Dedicated verification bucket
- [x] Signed URL flow
- [x] Upload validation
- [x] Admin verification queue
- [x] Approve/reject/request-more-info foundation
- [x] Verification badges
- [x] Expiry/suspension behavior
- [x] Permission enforcement
- [x] Security tests

Jira action: Close sprint as Done.

### Sprint 7: Guided AI Assistant Foundation

Status: Done with follow-up

Checklist:

- [x] Assistant app
- [x] Conversation persistence
- [x] Message persistence
- [x] Provider abstraction
- [x] Provider modes: disabled/demo/anthropic
- [x] Anthropic provider code preserved
- [x] Demo provider mode
- [x] Assistant config endpoint
- [x] Supported guided intents
- [x] Navigation allow-list
- [x] Unsupported fallback
- [x] Dashboard assistant
- [x] Public landing assistant
- [x] Premium AI orb
- [x] RealityNG-colored orb
- [x] Duplicate-send prevention
- [ ] Live Anthropic activation
- [ ] Token/cost monitoring for live provider

Jira action:

- Close Sprint 7 implementation as Done.
- Create deferred story: Anthropic Production Activation.

### v2.0.0 Release

Status: Done

Checklist:

- [x] Backend merged to `main`
- [x] Frontend merged to `main`
- [x] Backend tagged `v2.0.0`
- [x] Frontend tagged `v2.0.0`
- [x] Backend deployed from `main`
- [x] Frontend deployed from `main`
- [x] Backend health passing
- [x] Caretekk unaffected
- [x] Rollback assets preserved

Jira action: Close release as Done.

### Frontend Discovery Redesign Phases 1-7

Status: Done with QA signoff recommended

Checklist:

- [x] Phase 1: Responsive shell and design system
- [x] Phase 2: Search-first homepage
- [x] Phase 3: Search results and property cards
- [x] Phase 4: Property detail and conversion
- [x] Phase 5: Auth gating and dashboards
- [x] Phase 6: Trust/legal/public confidence pages
- [x] Phase 7: SEO/performance/release hardening
- [x] Remove premature forced signup for discovery
- [x] Keep browsing/search/detail public
- [x] Gate only value actions
- [x] Fix search tab scrollbar issue
- [x] Add landing-page AI assistant
- [x] Add premium RealityNG-colored AI orb
- [x] Align logo tagline under wordmark

Jira action:

- Add as completed epic.
- Move latest visual review into Sprint 7.5 QA.

---

## Immediate Next Sprint

### Sprint 7.5: Stabilization, QA, and PM Signoff

Status: Ready for Sprint Planning

Goal:

Confirm latest production deployment, verify real API behavior, collect PM/design approval, and prepare Sprint 8 tickets.

Checklist:

- [ ] Confirm latest Vercel deployment uses frontend `main`
- [ ] Confirm `NEXT_PUBLIC_USE_MOCKS=false`
- [ ] Confirm `NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1`
- [ ] Test register from production
- [ ] Test login from production
- [ ] Test browse/search/detail
- [ ] Test favorite
- [ ] Test inquiry
- [ ] Test viewing
- [ ] Test rental application
- [ ] Test verification submission
- [ ] Test admin verification
- [ ] Test public RealityNG AI
- [ ] Test dashboard assistant
- [ ] Confirm CORS is fixed
- [ ] Confirm mobile logo/tagline behavior
- [ ] Confirm AI orb does not block page interactions
- [ ] Capture screenshots for signoff
- [ ] Create Sprint 8 Jira tickets

Acceptance criteria:

- Production frontend uses real backend.
- No critical auth/marketplace/verification/assistant failures.
- PM/design signs off current UI.
- Sprint 8 backlog is ready.

---

## Remaining Roadmap

### Sprint 8: Google Maps and Location Intelligence

Status: Not started

Checklist:

- [ ] Google Maps provider setup
- [ ] API key restrictions and billing controls
- [ ] Coordinate/privacy policy
- [ ] Property coordinate fields/API support
- [ ] Browse map/list toggle
- [ ] Desktop split view
- [ ] Mobile map view
- [ ] Property pins
- [ ] Nearby landmarks
- [ ] Nearby schools/hospitals
- [ ] Directions integration
- [ ] Map QA

### Sprint 9: Artisan Marketplace

Status: Not started

Checklist:

- [ ] Artisan profiles
- [ ] Trade categories
- [ ] Artisan browse
- [ ] Artisan detail
- [ ] Quote request
- [ ] Booking workflow
- [ ] Reviews
- [ ] Verified artisan badges
- [ ] Admin moderation

### Sprint 10: Inspection Workflow

Status: Not started

Checklist:

- [ ] Inspection request model
- [ ] Property inspection flow
- [ ] Site inspection flow
- [ ] Construction inspection flow
- [ ] Admin assignment
- [ ] Report upload
- [ ] Evidence management
- [ ] Inspection status tracking

### Sprint 11: Construction Project Tracking

Status: Not started

Checklist:

- [ ] Construction project model
- [ ] Milestones
- [ ] Progress updates
- [ ] Evidence uploads
- [ ] Inspection integration
- [ ] Owner project dashboard

### Sprint 12: Lead Management and Inquiries Expansion

Status: Not started

Checklist:

- [ ] Contact agent workflow
- [ ] Lead inbox
- [ ] Agent pipeline
- [ ] Follow-up tracking
- [ ] Lead assignment
- [ ] Conversion analytics

### Sprint 13: Notifications and Messaging

Status: Not started

Checklist:

- [ ] Notification model/API
- [ ] Notification center
- [ ] Email provider setup
- [ ] Notification preferences
- [ ] Messaging thread model
- [ ] Messaging UI
- [ ] Read/unread state

### Sprint 14: Payments and Transaction Tracking

Status: Not started

Checklist:

- [ ] Payment provider decision
- [ ] Payment milestone model
- [ ] Payment proof upload
- [ ] Transaction history
- [ ] Dispute workflow
- [ ] Admin review
- [ ] Compliance wording review

### Sprint 15: Admin Operations and Beta Launch

Status: Not started

Checklist:

- [ ] Admin operations center
- [ ] Audit log search
- [ ] Monitoring and alerting
- [ ] Backup/restore drill
- [ ] Security readiness review
- [ ] Production runbook
- [ ] Support workflow
- [ ] Beta launch checklist

---

## Deferred Items

### Anthropic Production Activation

Status: Deferred

- [ ] Management approval
- [ ] Secure API key provisioning
- [ ] Set `AI_PROVIDER_MODE=anthropic`
- [ ] Live provider smoke test
- [ ] Token/cost validation
- [ ] Provider outage fallback

### Cloudflare Full Strict Origin Security

Status: Deferred

- [ ] Origin certificate
- [ ] Origin HTTPS on port 443
- [ ] Cloudflare Full Strict mode
- [ ] HSTS after stability

### Remote Property Monitoring

Status: Future phase

- [ ] CCTV integration
- [ ] IoT integration
- [ ] Smart monitoring dashboard
- [ ] Privacy/security policy

---

## Removed Scope

Do not add to active Jira:

- [x] Lawyer marketplace removed
- [x] Lawyer dashboard removed
- [x] Lawyer assignment removed
- [x] Legal review workflow removed

