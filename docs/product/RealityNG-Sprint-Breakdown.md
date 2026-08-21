# RealityNG Sprint Breakdown

Version: 3.0
Date: 2026-07-28
Cadence: 2-week sprints unless adjusted by PM/leadership
Status: Updated after v2.0.0 release, Sprint 8 closure, and Sprint 9.1 marketplace foundation

---

## Delivery Status Overview

| Sprint / Phase | Status | Summary |
| --- | --- | --- |
| Sprint 0 | Complete | Infrastructure, backend/frontend foundation, Docker, env, CI, health |
| Sprint 1 | Complete | Authentication, roles, profiles, admin approval, audit logs |
| Sprint 2 | Complete | Property marketplace foundation, CRUD, moderation, public browse |
| Sprint 3 | Complete | Property media, gallery, cover image, MinIO storage |
| Sprint 3.5 | Complete | Branding, design system, homepage/browse/detail alignment |
| Sprint 3.6 | Complete | Frontend integration, route audit, navigation, accessibility |
| Sprint 4 | Complete | Favorites, saved properties, dashboard foundations |
| Demo Mode | Complete | Mock auth/data/dashboards for executive demo |
| Sprint 4.5 | Complete | CEO alignment, Base44 flow, comparison foundation, apartment share |
| Sprint 5 Phase 1 | Complete | Show Interest and inquiry workflow |
| Sprint 5 Phase 2 | Complete | Viewing request and scheduling workflow |
| Sprint 5 Phase 3 | Complete | Rental application workflow |
| Sprint 5 Phase 4 | Complete | Unified transaction lifecycle and dashboards |
| Sprint 5.5 | Complete | Security audit and hardening |
| Sprint 6 | Complete | Verification layer and private document storage |
| Sprint 7 | Complete with deferred provider activation | Guided AI assistant framework, demo provider, Anthropic code preserved |
| v2.0.0 Release | Complete | Backend/frontend merged, tagged, deployed from main |
| Frontend Redesign Phases 1-7 | Complete with QA signoff recommended | Redfin-style discovery redesign, public AI, brand refinements |
| Sprint 7.5 | Complete with follow-up items | Stabilization, production QA, PM signoff, Sprint 8 grooming |
| Sprint 7.5.1 | Complete with follow-up items | Release readiness closure, backend timeout investigation, Sprint 8 approval checklist |
| Sprint 8 | Complete | Google Maps and Location Intelligence engineering complete; production activation deferred as an operations story |
| Sprint 9 | In progress | Verified Services Marketplace |
| Sprint 9.1 | Complete | Marketplace foundation: service categories, public provider profiles, browse APIs, and services pages |
| Sprint 10 | Planned | Inspection Workflow |
| Sprint 11 | Planned | Construction Project Tracking |
| Sprint 12 | Planned | Lead Management and Inquiries Expansion |
| Sprint 13 | Planned | Notifications and Messaging |
| Sprint 14 | Planned | Payments and Transaction Tracking |
| Sprint 15 | Planned | Admin Operations and Beta Launch |

---

## Completed Sprint Details

## Sprint 0: Infrastructure and Architecture

Status: Complete

Objective:

Establish the technical foundation for local and production-ready development.

Delivered:

- Django backend.
- Next.js frontend.
- PostgreSQL, Redis, Celery, MinIO.
- Docker and Docker Compose.
- Split settings and environment examples.
- Health endpoint.
- DRF and OpenAPI.
- Logging.
- Base model conventions.
- Test/CI foundation.

Acceptance status:

- Complete. Close as Done.

## Sprint 1: Authentication and Roles

Status: Complete

Objective:

Enable user identity, roles, profiles, and admin-controlled access foundations.

Delivered:

- Registration.
- Login.
- Token handling.
- User profiles.
- Role selection/onboarding.
- Admin approval foundation.
- Audit logging.
- Auth frontend screens.
- Protected routes.

Acceptance status:

- Complete. Close as Done.

## Sprint 2: Property Marketplace Foundation

Status: Complete

Objective:

Create the property listing and public browsing baseline.

Delivered:

- Property model.
- Owner/admin CRUD.
- Validation.
- Soft delete.
- Listing statuses.
- Admin approval/rejection.
- Public approved-listings endpoint.
- Search/filter/order/pagination.
- Browse and property card UI.
- Listing creation baseline.

Acceptance status:

- Complete. Close as Done.

## Sprint 3: Property Media and Gallery Management

Status: Complete

Objective:

Allow property owners/admins to upload and manage property images.

Delivered:

- Property image model.
- Upload/list/update/delete APIs.
- Cover image workflow.
- Upload validation.
- MinIO integration.
- Public gallery serialization.
- Frontend image uploader/gallery manager.

Acceptance status:

- Complete. Close as Done.

## Sprint 3.5: Branding and Design System

Status: Complete

Objective:

Align frontend visuals with RealityNG brand identity.

Delivered:

- Brand colors and typography.
- Shared UI components.
- Navbar/footer.
- Homepage redesign.
- Browse redesign.
- Property detail redesign.
- Accessibility and responsive improvements.

Acceptance status:

- Complete. Close as Done.

## Sprint 3.6: Frontend Integration and Accessibility Audit

Status: Complete

Objective:

Ensure all key frontend routes, flows, and components are connected and usable.

Delivered:

- Route audit.
- Navigation audit.
- Mobile navigation fixes.
- Dashboard navigation review.
- Responsive fixes.
- Accessibility pass.
- Shared component consistency.
- Property flow audit.

Acceptance status:

- Complete. Close as Done.

## Sprint 4: Favorites and Dashboard Foundations

Status: Complete

Objective:

Allow users to save properties and access dashboard foundations.

Delivered:

- Favorite model/API.
- Favorite uniqueness.
- Saved properties page.
- Favorite button on card/detail.
- `is_favorited` property response.
- Dashboard quick stats and actions.
- Audit events.

Acceptance status:

- Complete. Close as Done.

## Demo Mode and Executive Showcase

Status: Complete

Objective:

Allow stakeholders to experience RealityNG without a deployed backend.

Delivered:

- Mock authentication.
- Mock users.
- Mock properties.
- Mock inquiries and analytics.
- Mock dashboards.
- Demo service abstraction.
- Branding assets.
- Hero slideshow.
- Auth page cleanup.

Acceptance status:

- Complete. Close as Done.

## Sprint 4.5: CEO Alignment and Prototype Restoration

Status: Complete

Objective:

Align RealityNG with CEO feedback, approved prototype flow, and updated product direction.

Delivered:

- Base44-inspired flow.
- Logo and slogan improvements.
- Signup conversion modal.
- Role selection modal.
- Protected action wrapper.
- Post-login return flow.
- Apartment-share listing type foundation.
- Comparison selection foundation.
- Removed lawyer/legal marketplace references.
- Solutions for artisans section.
- Show Interest button.

Acceptance status:

- Complete. Close as Done.

## Sprint 5 Phase 1: Inquiry / Show Interest Foundation

Status: Complete

Objective:

Turn Show Interest into a functional inquiry workflow.

Delivered:

- Inquiry entity.
- Status pipeline.
- Create/list/retrieve/update APIs.
- Internal notes.
- Object-level permissions.
- Show Interest modal.
- Buyer and owner/agent dashboard integration.
- Demo support.
- Audit events.

Acceptance status:

- Complete. Close as Done.

## Sprint 5 Phase 2: Viewing Request and Scheduling

Status: Complete

Objective:

Link property interest to property viewing requests.

Delivered:

- Viewing entity linked to inquiry.
- Viewing status pipeline.
- Create/list/retrieve APIs.
- Confirm/reschedule/cancel/complete actions.
- Viewing request modal.
- Dashboard integration.
- Scheduling foundation.
- Demo support.
- Audit events.

Acceptance status:

- Complete. Close as Done.

## Sprint 5 Phase 3: Rental Application Workflow

Status: Complete

Objective:

Allow users to submit rental applications and owners/agents to review them.

Delivered:

- Rental application model.
- Submit/list/retrieve APIs.
- Review actions.
- Withdraw action.
- Owner notes.
- Application page/form.
- Buyer and owner/agent dashboard integration.
- Demo support.
- Audit events.

Acceptance status:

- Complete. Close as Done.

## Sprint 5 Phase 4: Workflow Integration and Operational Dashboards

Status: Complete

Objective:

Connect inquiries, viewings, and applications into one transaction lifecycle.

Delivered:

- Unified workflow.
- Buyer transaction center.
- Landlord/agent/admin dashboard improvements.
- Activity timelines.
- Workflow linking.
- Dashboard metrics.
- Notification placeholder.
- Status badges.

Acceptance status:

- Complete. Close as Done.

## Sprint 5.5: Security Audit and Hardening

Status: Complete

Objective:

Harden auth, permissions, APIs, file uploads, infrastructure, and demo boundaries.

Delivered:

- Object permission review.
- Admin permission review.
- File upload review.
- Private document access hardening.
- Demo boundary review.
- CORS/CSRF review.
- Security tests.

Acceptance status:

- Complete. Close as Done.

## Sprint 6: Verification Layer

Status: Complete

Objective:

Create trust and verification workflows for users, agents, artisans, and properties.

Delivered:

- Verification request model.
- Property verification.
- Verification document model.
- Private verification storage.
- Dedicated verification bucket.
- Signed URL flow.
- Admin verification queue.
- Approve/reject/request-more-info foundations.
- Verification badges.
- Expiry/suspension behavior.
- Permission/security tests.

Acceptance status:

- Complete. Close as Done.

## Sprint 7: Guided AI Assistant Foundation

Status: Complete with Anthropic activation deferred

Objective:

Add assistant architecture and guided platform support.

Delivered:

- Assistant app.
- Conversation/message persistence.
- Provider abstraction.
- Provider modes: disabled, demo, anthropic.
- Anthropic provider code preserved.
- Demo provider mode.
- Assistant config endpoint.
- Supported guided intents.
- Navigation allow-list.
- Unsupported fallback.
- Dashboard assistant.
- Public landing-page assistant.
- Premium animated AI orb.
- Brand-colored orb.

Deferred:

- Live Anthropic credentials.
- Live provider smoke tests.
- Token/cost monitoring for Anthropic.

Acceptance status:

- Framework complete. Close Sprint 7 as Done and create a deferred Anthropic Activation story.

---

## Frontend Redesign Phases 1-7

Status: Complete with QA signoff recommended

Objective:

Rework public frontend structure toward a Redfin-style, search-first marketplace while preserving RealityNG's Nigerian trust-first positioning.

Delivered:

- Responsive shell and task navigation.
- Search-first homepage.
- Public browsing without forced signup.
- Search results and property cards redesign.
- Property detail conversion improvements.
- Auth gating policy refinement.
- Trust/legal/public confidence pages.
- SEO/performance hardening.
- Public RealityNG AI assistant.
- AI orb visual system.
- Logo/tagline refinements.

Acceptance status:

- Implemented and pushed. PM/design should visually approve production screenshots in Sprint 7.5.

---

## Sprint 7.5: Stabilization, QA, and PM Signoff

Status: Complete

Objective:

Confirm that the latest deployed product is stable, using the real backend, and ready for Sprint 8.

Scope:

- Production deployment confirmation.
- Browser smoke tests.
- CORS/auth verification.
- Mobile/responsive QA.
- PM/design signoff.
- Sprint 8 backlog grooming.

Acceptance criteria:

1. Production frontend uses real backend API.
2. Register/login works without CORS errors.
3. Public browse/search/detail works without account.
4. Value actions prompt login/account correctly.
5. Verification flows work.
6. Admin verification works.
7. Public RealityNG AI works without account.
8. Dashboard assistant works for authenticated users.
9. AI orb and logo/tagline are approved on mobile and desktop.
10. Sprint 8 tickets are ready.

Complexity:

Small.

Risk:

Mostly QA/environment risk, not feature-building risk.

---

## Sprint 7.5.1: Release Readiness and Final Production Approval

Status: Complete with follow-up items

Objective:

Close Sprint 7.5 operational readiness items before starting Sprint 8.

Delivered:

- Release readiness report.
- PM visual review checklist.
- Backend timeout investigation.
- Production data audit.
- Monitoring assessment.
- Technical debt register.
- Sprint 8 kickoff checklist.

Follow-up:

- PM/browser sign-off.
- VPS resource verification.
- Production data seeding.
- Monitoring and backup rehearsal.

---

## Sprint 8: Google Maps and Location Intelligence

Status: Complete with follow-up items

Objective:

Add map-based discovery and location intelligence.

Delivered:

- Backend location fields for properties.
- Public-safe coordinate serialization.
- Location precision and geocoding status model.
- State, LGA, neighborhood, map-ready, and bounding-box filters.
- Public map metadata and privacy messaging.
- Google Maps loader with graceful no-key/error fallback.
- Browse page Grid/List/Map/Split modes.
- List and map selected-property synchronization.
- Marker styles for normal, featured, verified/exact, selected, and clustered properties.
- Property detail location intelligence section.
- Mock data coordinates for local/demo QA.
- Google Maps configuration and privacy documentation.

Acceptance criteria:

1. Users can switch between list and map view. Complete.
2. Map pins match filtered property results. Complete in implementation; production activation requires the deferred Google Maps operations story.
3. Selecting a pin opens the correct property preview. Complete in component logic.
4. Exact/private location is not exposed without approval. Complete through public-safe serialization.
5. API key is restricted and billing controls are documented. Complete as documentation; execution moved to deferred production task.

Complexity:

Large.

Deferred production story:

- Google Maps Production Activation.
- Status: Deferred.
- Reason: awaiting paid Google Cloud billing approval, restricted production API credentials, production environment configuration, production coordinate audit, and live browser QA.
- Estimate: Small operational task, 1-2 days after credentials and billing are available.
- Priority: High.

Notes:

- Sprint 8 is no longer open. Engineering scope is complete and RealityNG can proceed to Sprint 9.
- The application remains fully usable without a Google Maps key because the no-key/error fallback is part of the delivered Sprint 8 implementation.

---

## Sprint 9: Verified Services Marketplace

Status: In progress

Objective:

Enable users to discover, evaluate, request quotes from, book, and review verified property-related service providers.

Scope:

- Service provider profiles for individual artisans and future companies.
- Trade category hierarchy.
- Service areas.
- Portfolio images.
- Verification badge framework.
- Public services browse and provider detail pages.
- Quote request workflow.
- Booking workflow foundation.
- Booking-based reviews and ratings.
- Complaints and admin moderation.
- Customer, provider, and admin dashboard extensions.
- AI assistant guidance for service discovery.

Implementation phases:

1. Sprint 9.1: Marketplace foundation. Complete.
2. Sprint 9.2: Profiles, portfolio, and service areas.
3. Sprint 9.3: Quotes and booking foundation.
4. Sprint 9.4: Reviews and trust.
5. Sprint 9.5: Dashboards.
6. Sprint 9.6: Admin moderation and complaints.
7. Sprint 9.7: Testing, QA, and release hardening.

Sprint 9.1 delivered:

- Backend `apps.services` application.
- Database-backed trade category hierarchy with seed migration.
- Public service provider profile model.
- Provider trades and service areas.
- Public browse endpoints for active providers.
- Public category endpoint.
- Provider detail endpoint by slug.
- Admin registration for marketplace foundation models.
- OpenAPI coverage for service endpoints.
- Frontend `/services` marketplace landing page.
- Frontend `/services/providers/[slug]` public provider profile page.
- Reusable services marketplace UI components.
- Mock service data support for demo/local mock mode.
- Backend model, serializer, permission, and API tests.
- Frontend render, filter, empty-state, and provider-profile tests.

Sprint 9.1 intentionally did not deliver:

- Quote requests.
- Bookings.
- Reviews.
- Complaints.
- Payments.
- Provider profile editing.
- Portfolio uploads.

Planning document:

- `docs/RealityNG-Sprint-9-Verified-Services-Marketplace-Plan.md`
- `docs/RealityNG-Sprint-9.1-Marketplace-Foundation-Report.md`

Open decisions before implementation:

- Sprint 9.2 should define provider self-service editing rules.
- Sprint 9.2 should confirm which portfolio media types are allowed.
- Sprint 9.3 should confirm quote request versus booking-first priority.
- Leadership should confirm which categories require mandatory certification.
- Product should confirm whether provider phone/WhatsApp remains public before quote request.
- Product should confirm whether reviews are auto-published or moderated.

Complexity:

Large.

---

## Sprint 10: Inspection Workflow

Status: Planned

Objective:

Support property, site, and construction inspections.

Scope:

- Inspection requests.
- Admin assignment.
- Report upload.
- Evidence management.
- Inspection status tracking.

Complexity:

Large.

---

## Sprint 11: Construction Project Tracking

Status: Planned

Objective:

Provide construction visibility for owners and diaspora investors.

Scope:

- Project model.
- Milestones.
- Progress updates.
- Evidence uploads.
- Inspection integration.
- Project dashboard.

Complexity:

Large.

---

## Sprint 12: Lead Management and Inquiries Expansion

Status: Planned

Objective:

Improve owner/agent pipeline management.

Scope:

- Lead inbox.
- Agent pipeline.
- Contact agent workflow.
- Follow-up tracking.
- Lead assignment.
- Conversion analytics.

Complexity:

Medium to Large.

---

## Sprint 13: Notifications and Messaging

Status: Planned

Objective:

Turn workflow events into user-facing notifications and messaging.

Scope:

- Notification model/API.
- Notification center.
- Email provider.
- Notification preferences.
- Messaging threads.
- Read/unread state.

Complexity:

Large.

---

## Sprint 14: Payments and Transaction Tracking

Status: Planned

Objective:

Track payment milestones and proofs.

Scope:

- Payment provider decision.
- Payment milestones.
- Proof upload.
- Transaction history.
- Disputes.
- Admin review.

Complexity:

Extra Large.

Important:

Do not imply escrow or custody unless legally approved.

---

## Sprint 15: Admin Operations and Beta Launch

Status: Planned

Objective:

Prepare RealityNG for controlled beta operations.

Scope:

- Admin operations center.
- Audit log search.
- Monitoring.
- Backup/restore drill.
- Security readiness review.
- Support workflow.
- Beta launch checklist.
- Production runbook.

Complexity:

Large.

---

## Deferred Future Work

### Anthropic Production Activation

Status: Deferred

Reason:

Management approval and API credentials are pending.

### Cloudflare Full Strict Origin Security

Status: Deferred production hardening

Reason:

Current Cloudflare setup works, but origin HTTPS/Full Strict should be completed later.

### Remote Property Monitoring

Status: Future phase

Reason:

Requires hardware/vendor/privacy/support decisions.

---

## Removed Scope

The following are removed from the active roadmap:

- Lawyer marketplace.
- Lawyer dashboards.
- Lawyer assignment flows.
- Legal review workflow.

---

## Cross-Sprint Definition of Done

Every future sprint should include:

1. Approved scope and acceptance criteria.
2. Backend permissions and object-level access tests.
3. API documentation updates.
4. Frontend loading/empty/error states.
5. Mobile/tablet/desktop QA.
6. Accessibility checks.
7. Security review for sensitive workflows.
8. Lint/typecheck/tests/build.
9. Deployment notes.
10. Rollback notes.
