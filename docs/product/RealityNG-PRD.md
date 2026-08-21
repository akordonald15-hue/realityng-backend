# RealityNG Product Requirements Document

Version: 2.0
Date: 2026-06-24
Owner: Product, Engineering, Operations
Status: CEO-aligned and approved for sprint planning

## 1. Product Summary

RealityNG is a diaspora-focused Nigerian PropTech platform for discovering, verifying, renting, buying, building, and managing property in Nigeria.

The product combines a trusted property marketplace with guided workflows for remote buyers, tenants, landlords, agents, artisans, inspectors, and administrators. RealityNG is designed to reduce uncertainty through verified listings, transparent workflows, evidence, and clear status tracking.

The AI assistant is an official product capability and will become the primary discovery and guidance layer across RealityNG. Users should be able to describe what they need in natural language and receive relevant properties, comparisons, workflow guidance, and service-provider recommendations.

## 2. Current Product State

The following work is complete:

1. Sprint 0 - Infrastructure and Architecture.
2. Sprint 1 - Authentication and Roles.
3. Sprint 2 - Property Marketplace Foundation.
4. Sprint 3 - Property Media and Gallery Management.
5. Sprint 3.5 - Branding and Design System.
6. Sprint 3.6 - Frontend Integration, Navigation, and Accessibility.
7. Sprint 4 - Favorites and Dashboard Foundations.
8. Demo mode with mock authentication, properties, inquiries, users, analytics, and role dashboards.
9. RealityNG domain connection.
10. Vercel production frontend deployment.
11. Branded application icons, logo treatments, and premium homepage imagery.

Implemented backend capabilities include authentication, role requests and approvals, profiles, audit logs, property CRUD, listing moderation, public property browsing, property images, favorites, and dashboard summary data.

Implemented frontend capabilities include authentication and onboarding, property browsing and detail pages, property creation, gallery management, favorites, saved properties, profile and dashboard screens, responsive branding, and a backend-independent executive demo mode.

## 3. Product Goals

1. Help users discover suitable Nigerian properties quickly and confidently.
2. Enable landlords and agents to publish and manage quality inventory.
3. Give diaspora users transparent remote workflows and evidence.
4. Convert property discovery into viewings, rental applications, and qualified leads.
5. Establish verification signals for agents, properties, and organizations.
6. Provide trusted artisan and inspection marketplaces.
7. Support construction and payment progress tracking without directly holding customer funds.
8. Use conversational AI to reduce navigation friction and guide users through complex workflows.
9. Build an extensible platform for future remote monitoring and property management.

## 4. Product Principles

1. Trust before transaction.
2. Remote-first execution.
3. AI-guided, not AI-only.
4. Clear human review for high-risk decisions.
5. Mobile-first and accessible.
6. Nigerian location, pricing, identity, and business realities are first-class requirements.
7. Marketplace quality is more important than unmoderated listing volume.
8. Sensitive decisions and state changes require auditability.
9. Product copy must not imply that RealityNG provides legal guarantees, escrow custody, or regulatory certification unless supported by an approved partner.

## 5. Target Users

### 5.1 Tenant

Finds rental or apartment-share listings, requests viewings, submits applications, tracks application status, and saves suitable properties.

### 5.2 Buyer and Diaspora Investor

Discovers properties, compares options, reviews trust signals, requests verification or inspection, and remotely follows transaction progress.

### 5.3 Landlord

Creates and manages listings, reviews viewing requests and applications, monitors listing performance, and manages property activity.

### 5.4 Agent

Manages inventory and leads, completes verification, coordinates viewings, reviews applications, and tracks conversion performance.

### 5.5 Artisan

Creates a verified service profile, receives quote or booking requests, completes work, and earns reviews.

### 5.6 Inspector

Receives assignments, performs property, site, or construction inspections, uploads evidence, and submits structured reports.

### 5.7 Administrator

Moderates listings, verifies users and properties, manages operational queues, reviews audit records, monitors platform health, and supports disputes.

## 6. Approved Product Scope

### 6.1 Marketplace and Discovery

1. Public property browsing.
2. Search, filters, ordering, and pagination.
3. Property detail and image galleries.
4. Favorites and saved properties.
5. Property comparison.
6. Google Maps, property pins, landmarks, and directions.
7. Conversational property search.
8. AI recommendations and natural-language filtering.

### 6.2 Listing Types

1. Sale.
2. Rent.
3. Apartment share.

Supported property categories may include land, duplexes, apartments, shortlets, commercial properties, and hotels where marketplace operations support them.

Apartment-share listings must support share-specific details such as available spaces, preferred occupancy, shared amenities, house rules, and move-in expectations. Exact fields will be finalized during Sprint 4.5 implementation design.

### 6.3 Demand Workflows

1. Viewing requests.
2. Viewing scheduling.
3. Rental applications.
4. Application status tracking.
5. Landlord and agent application review.
6. Property inquiries and lead pipelines.

### 6.4 Trust and Verification

1. CAC verification.
2. Agent verification.
3. Property verification.
4. Verification badges.
5. Property, site, and construction inspections.
6. Evidence and report management.

Verification badges must identify what was checked, when it was checked, and whether it has expired or been revoked. A badge must not be presented as a guarantee of ownership or investment outcome.

### 6.5 Property Services

1. Artisan profiles.
2. Artisan verification.
3. Quotes and booking workflows.
4. Reviews.
5. Construction milestone tracking.
6. Project dashboards.

### 6.6 Communication and Transactions

1. Contact-agent and inquiry workflows.
2. In-app messages and conversation threads.
3. In-app and email notifications.
4. Payment milestones and proof tracking.
5. Dispute tracking.
6. Transaction history.

RealityNG will track payment activity but will not claim to hold funds in escrow unless a regulated partner integration is formally approved.

## 7. AI Assistant

### 7.1 Product Role

The RealityNG assistant is the primary discovery and guidance layer. It supplements standard navigation and filters; it does not remove access to deterministic browse, filter, dashboard, or admin interfaces.

### 7.2 Initial Capabilities

1. Interpret natural-language property searches.
2. Convert user requests into structured listing filters.
3. Recommend matching properties.
4. Explain why a property matched.
5. Assist with property comparisons.
6. Explain platform workflows such as applying, requesting a viewing, or saving a property.
7. Maintain conversation context within a session.
8. Link users to the relevant screen or action.

Example queries:

1. "Show me 3-bedroom apartments in Lekki."
2. "Find land under NGN 15 million in Uyo."
3. "Compare these two properties."
4. "How do I apply for a property?"
5. "Find a plumber in Abuja."
6. "What properties have swimming pools?"

### 7.3 Future AI Capabilities

1. Voice input.
2. Voice responses.
3. Personalized recommendations.
4. Vendor recommendations.
5. Application guidance.
6. Property comparison summaries.
7. Proactive discovery based on saved preferences, subject to consent.

### 7.4 AI Guardrails

1. Property facts must come from RealityNG data or clearly identified external sources.
2. The assistant must not invent price, availability, verification, ownership, or amenity data.
3. Search results must retain deterministic links to their source listings.
4. Financial, legal, and investment responses must be framed as general guidance, not professional advice.
5. Sensitive user data must not be sent to model providers without an approved privacy and retention configuration.
6. Prompt injection, abuse, rate limiting, moderation, observability, and cost controls are required.
7. AI responses must provide a fallback path to standard search or human support.

### 7.5 AI Success Measures

1. Search-to-detail conversion.
2. Successful query interpretation rate.
3. Percentage of assistant sessions producing at least one relevant listing.
4. Assistant-to-viewing, save, comparison, or application conversion.
5. User correction and fallback rate.
6. Response latency and cost per assisted session.

## 8. Navigation and Conversion

Sprint 4.5 will restore the approved Base44-inspired user flow while retaining the production design system and accessibility standards.

Requirements:

1. Clear routes to browse, saved properties, list a property, dashboards, profile, and authentication.
2. Role-aware dashboard navigation.
3. Mobile navigation with no orphaned routes.
4. Prominent, consistently sized RealityNG logo.
5. White-background logo treatment where required for visibility.
6. A non-intrusive sign-up conversion popup.
7. Frequency controls so the popup does not repeatedly interrupt dismissed or authenticated users.
8. Conversion events for sign-up prompt impressions, dismissals, and completed registrations.

## 9. Property Comparison

Users can select and compare two to four properties.

Comparison fields:

1. Price and currency.
2. Listing and property type.
3. Location.
4. Bedrooms, bathrooms, parking, land size, and floor area.
5. Amenities.
6. Verification status.
7. Cover image.
8. Agent or owner summary where publicly available.

The comparison foundation belongs to Sprint 4.5. AI-generated comparison guidance belongs to Sprint 7 and must be based on the same structured comparison data.

## 10. Google Maps and Location Intelligence

Google Maps is the approved map provider for Sprint 8.

Capabilities:

1. Property map view.
2. List-and-map split view.
3. Property pins and selected-property highlighting.
4. Nearby landmarks.
5. Nearby schools and hospitals.
6. Directions handoff.
7. Privacy-aware coordinate precision for sensitive listings.

Map quotas, API key restrictions, billing alerts, geocoding storage rules, and fallback behavior are required before production launch.

## 11. Removed Product Scope

The following features are removed from the approved RealityNG product direction:

1. Legal review workflow.
2. Lawyer marketplace.
3. Lawyer dashboards.
4. Lawyer assignment flows.
5. Legal opinion issuance.

No new roadmap item, Jira epic, navigation entry, user journey, API, or database entity should be created for these features. Existing legacy references and role options must be removed through Sprint 4.5 migration and cleanup work without breaking existing users or data integrity.

RealityNG may integrate with external professional services in the future through a separately approved partner model, but that is not part of the current product roadmap.

## 12. Deferred Future Scope

The following capabilities are approved for a future phase after the current roadmap:

1. Remote property monitoring.
2. CCTV integration.
3. Smart property management.
4. IoT monitoring.
5. Native mobile applications.
6. Advanced voice assistant experiences.
7. Mortgage, refinance, insurance, and regulated escrow partner integrations.

These items must not be pulled into Sprints 4.5 through 15 without formal roadmap approval.

## 13. Functional Requirements by Module

### 13.1 Authentication and Roles

Users can register, authenticate, manage profiles, request supported roles, and access role-appropriate screens. Professional and administrator roles require approval where configured.

### 13.2 Listings and Media

Owners and permitted agents can create, edit, submit, archive, and manage images for listings. Admins can approve or reject listings. Public endpoints return approved listings only.

### 13.3 Favorites

Authenticated users can save and remove properties. One favorite is allowed per user and property. Favorite state appears consistently on cards, detail pages, dashboards, and the saved-properties page.

### 13.4 Comparison

Users can compare two to four active properties. Deleted, archived, or unavailable properties must be clearly identified or removed from new comparisons.

### 13.5 Viewings and Applications

Users can request viewings and submit rental applications. Landlords and agents can accept, reschedule, reject, or decide requests according to valid status transitions.

### 13.6 Verification

Authorized users can submit verification requests and supporting documents. Admins can review, approve, reject, expire, or revoke verification status.

### 13.7 AI Assistant

Users can search and navigate in natural language. The assistant must return explainable, source-linked results and use existing permission boundaries.

### 13.8 Maps

Users can browse properties spatially and inspect nearby context without exposing restricted coordinates.

### 13.9 Artisans

Users can discover verified artisans, request quotes or bookings, and review eligible completed services.

### 13.10 Inspections

Users can request inspections. Approved inspectors can submit structured reports and evidence. Admins can review and release reports.

### 13.11 Construction Tracking

Authorized project participants can manage milestones, progress, evidence, and linked inspection outcomes.

### 13.12 Inquiries and Lead Management

Users can contact agents or listing owners. Agents can manage lead stages and view conversion metrics.

### 13.13 Notifications and Messaging

The platform provides permission-scoped conversation threads, workflow notifications, and email alerts.

### 13.14 Payments and Disputes

Authorized users can record payment milestones, upload proof, track decisions, and open disputes. Payment events require append-only audit history.

### 13.15 Administration

Admins can operate approval queues, search audit logs, monitor provider and job health, and act only within explicit permissions.

## 14. Non-Functional Requirements

### 14.1 Security

1. Object-level authorization for all protected resources.
2. Rate limiting for authentication, uploads, AI, messaging, and high-cost APIs.
3. Secure upload validation and signed private file access.
4. Secret management outside source control.
5. Audit logs for sensitive state transitions.
6. Restricted Google Maps and AI provider keys.
7. Regular dependency, permission, and configuration review.

### 14.2 Performance

1. Paginate all list endpoints.
2. Avoid per-item database queries in listing and favorite responses.
3. Optimize responsive images and galleries.
4. Cache appropriate public and map data.
5. Stream or progressively render AI responses where practical.
6. Define and monitor web-vital, API latency, and assistant latency targets.

### 14.3 Reliability

1. Health checks for web, API, database, Redis, workers, and storage.
2. Retry idempotent background jobs.
3. Graceful degradation when AI, maps, email, or storage providers are unavailable.
4. Tested database backup and restoration.
5. Structured logs, correlation IDs, error monitoring, and alerting.

### 14.4 Accessibility

1. Keyboard-accessible controls and dialogs.
2. Visible focus states.
3. Screen-reader labels for icon actions.
4. Sufficient color contrast.
5. Responsive layouts across mobile, tablet, and desktop.
6. Standard search and navigation alternatives to AI interactions.

### 14.5 Privacy

1. Collect only data required for approved workflows.
2. Define retention and deletion rules for identity and property documents.
3. Obtain consent for personalization and AI use where required.
4. Avoid exposing exact private-property coordinates or personal contact details publicly.

## 15. Success Metrics

### Marketplace

1. Approved active listings.
2. Search-to-detail conversion.
3. Detail-to-save, compare, viewing, inquiry, or application conversion.
4. Listing approval time.
5. Listing freshness and rejection reasons.

### Trust

1. Verified agents and properties.
2. Verification completion time.
3. Inspection request and completion rate.
4. Fraud and duplicate-listing report rate.

### AI

1. Assistant adoption.
2. Query success rate.
3. Assistant conversion to meaningful action.
4. Fallback and correction rate.
5. Cost and latency per assistant session.

### Supply and Operations

1. Active agents and landlords.
2. Lead response time.
3. Application decision time.
4. Active verified artisans.
5. Admin queue age and SLA compliance.

## 16. Delivery Roadmap

| Sprint | Status | Focus |
| --- | --- | --- |
| 0 | Complete | Infrastructure and architecture |
| 1 | Complete | Authentication and roles |
| 2 | Complete | Property marketplace foundation |
| 3 | Complete | Property media and gallery management |
| 3.5 | Complete | Branding and design system |
| 3.6 | Complete | Frontend integration, navigation, and accessibility |
| 4 | Complete | Favorites and dashboard foundations |
| Demo Mode | Complete | Mock data, authentication, dashboards, and production showcase |
| 4.5 | Next | CEO alignment, Base44 flow, conversion, comparison, apartment sharing, lawyer cleanup |
| 5 | Planned | Viewing and rental applications |
| 6 | Planned | Verification layer |
| 7 | Planned | AI assistant foundation |
| 8 | Planned | Google Maps and location intelligence |
| 9 | Planned | Artisan marketplace |
| 10 | Planned | Inspection workflow |
| 11 | Planned | Construction project tracking |
| 12 | Planned | Lead management and inquiries |
| 13 | Planned | Notifications and messaging |
| 14 | Planned | Payments and transaction tracking |
| 15 | Planned | Admin operations and beta launch |

Detailed sprint scope and acceptance criteria are maintained in `RealityNG-Sprint-Breakdown.md`. Jira epic mapping is maintained in `RealityNG-Jira-Epics-and-Roadmap.md`.

## 17. Risks and Mitigations

1. AI returns inaccurate property facts.
   Mitigation: Retrieval from structured RealityNG data, source links, validation, and deterministic fallbacks.
2. Map and AI provider costs grow unexpectedly.
   Mitigation: Quotas, caching, rate limits, usage dashboards, and billing alerts.
3. Location data is inconsistent.
   Mitigation: Normalize state, city, LGA, neighborhood, and coordinates before map rollout.
4. Verification badges are misunderstood.
   Mitigation: Display verification scope, date, status, and disclaimers.
5. Operational queues exceed staffing capacity.
   Mitigation: SLA dashboards, queue prioritization, assignment controls, and staged rollout.
6. Users continue transactions off-platform.
   Mitigation: Make saved context, scheduling, applications, evidence, and status tracking valuable.
7. Legacy lawyer references create inconsistent navigation or permissions.
   Mitigation: Inventory and remove references in Sprint 4.5 with migration and regression tests.
8. Sign-up prompts reduce trust.
   Mitigation: Frequency caps, accessible dismissal, authenticated-user suppression, and conversion measurement.

## 18. Open Product Decisions

1. Which Base44 navigation details are mandatory versus inspirational?
2. What event and timing trigger should open the sign-up popup?
3. Should apartment-share listings be a listing type, property subtype, or both?
4. Which Nigerian cities receive first map and location-data normalization?
5. Which AI model provider, embedding strategy, and data-retention configuration are approved?
6. Which verification checks can RealityNG perform directly and which require partners?
7. What are the launch SLAs for viewings, applications, verification, inspections, and inquiries?

## 19. Launch Readiness

Beta launch requires:

1. Critical user journeys passing end-to-end tests.
2. No unresolved high-severity security issue.
3. Production backend, database, Redis, workers, and object storage.
4. Monitoring, backups, alerts, and operational runbooks.
5. Terms, privacy policy, verification disclaimers, and payment disclaimers.
6. Admin staffing and escalation procedures.
7. Google Maps and AI provider budgets, key restrictions, and failure fallbacks.
8. Accessibility and responsive checks on supported browsers and devices.
