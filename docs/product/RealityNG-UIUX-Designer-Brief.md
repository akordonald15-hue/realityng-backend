# RealityNG UI/UX Designer Brief

Version: 1.0  
Date: 2026-07-31  
Prepared for: External UI/UX Designer  
Product: RealityNG  

---

## 1. Product Overview

RealityNG is a Nigerian PropTech platform built for property discovery, verification, transactions, and trusted property-related services.

The platform is especially focused on Nigerians in the diaspora and local users who want to discover, verify, rent, buy, list, manage, or inspect property in Nigeria with greater confidence.

RealityNG is not only a property listing website. It is becoming a trust-first marketplace for:

- Verified properties.
- Verified landlords and agents.
- Property inquiries.
- Viewing requests.
- Rental applications.
- User and property verification.
- Google Maps/location-aware discovery.
- AI-guided property assistance.
- Verified property-service providers such as electricians, plumbers, cleaners, CCTV installers, solar installers, movers, surveyors, architects, and construction professionals.

The brand promise is:

```text
Where Dreams Find an Address
```

## 2. Core Product Idea

RealityNG helps users answer four important questions:

1. What property or service do I need?
2. Can I trust the listing, provider, or representative?
3. What is my next safe action?
4. How do I track the process from discovery to completion?

The design must make the platform feel:

- Trustworthy.
- Premium.
- Nigerian.
- Simple.
- Search-first.
- Mobile-friendly.
- Clear for diaspora users.
- Professional enough for investors, agents, landlords, and management stakeholders.

## 3. Current Product Stage

RealityNG has already completed the following engineering releases:

- Infrastructure and backend/frontend setup.
- Authentication and roles.
- Property marketplace foundation.
- Property media/gallery.
- Favorites and saved properties.
- Inquiry and Show Interest workflow.
- Viewing request workflow.
- Rental application workflow.
- Transaction dashboards.
- Verification layer.
- Guided AI assistant framework.
- Google Maps/location intelligence engineering.
- Services marketplace foundation.
- Production backend and frontend connection.
- Frontend redesign phases inspired by Redfin's search-first structure.

The product is functional. The next goal is to improve the UI/UX design quality, consistency, usability, and visual polish before wider beta usage.

## 4. Design Direction

RealityNG should take product-structure inspiration from Redfin, especially:

- Simple, wide desktop navigation.
- Search-first homepage.
- Minimal hero copy.
- Strong property search box.
- Browsing before forcing signup.
- Clean property cards.
- Clear property detail hierarchy.
- Mobile-first discovery.
- Account prompts only after value-based actions.

Do not copy Redfin visually or literally.

RealityNG must remain a distinct Nigerian, trust-first property marketplace.

## 4.1 Required Process Flow

Management specifically wants the complete RealityNG process flow to remain visible in the product design. The redesign should simplify the presentation, but it must not remove the process flow.

This flow is important because RealityNG is not just a listing website. The platform must clearly show users how they move from discovery to a trusted decision.

The core property journey should remain:

```text
Search / Browse
↓
Open Property Detail
↓
Show Interest
↓
Request Viewing
↓
Apply
↓
Verification / Review
↓
Approval or Decision
↓
Dashboard Tracking
```

For public users, the homepage and property detail pages should explain the journey in a simple, visual way. The designer may use a timeline, step cards, horizontal flow, vertical mobile flow, or compact process section, but the process itself must remain.

Important process-flow requirements:

- Do not remove the "How It Works" or process-flow section.
- Make the flow easier to understand, not hidden.
- On desktop, it can appear as a clean horizontal or staged journey.
- On mobile, it should become a vertical step-by-step flow.
- It should explain what happens before and after a user expresses interest.
- It should connect naturally to verification, viewing, applications, and dashboard tracking.
- It should not claim that every property is legally verified unless the backend verification status confirms it.
- It should avoid lawyer/legal-review language because lawyer workflows were removed from the current roadmap.

Suggested public-facing wording:

```text
Find a property
Review trust signals
Show interest
Request a viewing
Apply or proceed
Track every step from your dashboard
```

For service providers, a separate future service journey can be designed later:

```text
Browse verified providers
Open provider profile
Check service area and trust badges
Request a quote
Book service
Review completed work
```

The services journey should be shown only as a future-ready concept unless quote and booking workflows are approved for implementation.

## 5. Brand Direction

Existing brand colors:

| Role | Color |
| --- | --- |
| Primary green | `#0B3B2E` |
| Dark green | `#06271F` |
| Accent gold | `#C99A3D` |
| Light gold | `#E5C477` |
| Warm background | `#F7F6F1` |
| Main text | `#17201D` |
| Verification green | `#178A58` |
| Warning | `#B76A18` |

Branding rules:

- Use the official RealityNG logo assets already in the project.
- Desktop navbar should show the logo and the tagline beneath the RealityNG wordmark.
- Mobile navbar should show only the compact logo.
- No white rounded box around the logo.
- The tagline should read exactly: `Where Dreams Find an Address`.
- The interface should use green and gold carefully, not excessively.
- Avoid cartoon styling.
- The AI assistant should feel premium and modern, using the RealityNG brand palette.

## 6. Key User Types

### Public Visitor

Can browse, search, view properties, view service providers, read trust information, and use the public guided assistant.

### Buyer / Tenant

Can save properties, submit inquiries, request viewings, apply for rentals, track saved properties, and use dashboards.

### Landlord

Can list properties, upload media, request property verification, manage inquiries, manage viewings, and review applications.

### Agent

Can manage listings, verification, inquiries, viewings, applications, and profile trust signals.

### Admin

Can review verification requests, inspect private documents through secure signed access, approve/reject verification, and moderate platform operations.

### Service Provider / Artisan

Can eventually manage a provider profile, service areas, portfolio, quotes, bookings, and reviews. Sprint 9.1 currently supports public provider browsing only.

## 7. Account-Gating Policy

The redesign must avoid forcing users to sign up before they receive value.

Public users should be able to:

- Visit homepage.
- Search properties.
- Browse property results.
- Open property details.
- Browse service providers.
- Open provider profiles.
- Read verification standards.
- Understand the platform.
- Use the public guided assistant.

Authentication should be required only for value-based actions:

- Save property.
- Save search.
- Create alert.
- Request viewing.
- Submit inquiry.
- Submit rental application.
- List property.
- Enter dashboard.
- Submit verification.
- Manage provider/service profile.

When authentication is required, the design should preserve the user's original intent after login/signup.

## 8. Current App Page Inventory

The current app has 29 implemented route templates.

| # | Route | Purpose | Priority |
| --- | --- | --- | --- |
| 1 | `/` | Homepage and search-first landing | High |
| 2 | `/properties` | Property browse/search/results | High |
| 3 | `/properties/[slug]` | Property detail | High |
| 4 | `/services` | Verified services marketplace browse | High |
| 5 | `/services/providers/[slug]` | Service provider profile | High |
| 6 | `/auth/sign-up` | Account registration | High |
| 7 | `/auth/sign-in` | Login | High |
| 8 | `/auth/forgot-password` | Password recovery start | Medium |
| 9 | `/auth/reset-password` | Password reset | Medium |
| 10 | `/onboarding/role-setup` | Role selection/onboarding | High |
| 11 | `/dashboard` | Role-aware dashboard | High |
| 12 | `/saved-properties` | Saved property list | High |
| 13 | `/properties/new` | Add/list property | High |
| 14 | `/apply/[propertyId]` | Rental application form | High |
| 15 | `/settings/profile` | User profile settings | Medium |
| 16 | `/verification` | Verification centre | High |
| 17 | `/verification/new` | New user/provider verification | High |
| 18 | `/verification/property/[propertyId]/new` | Property verification submission | High |
| 19 | `/admin` | Admin dashboard | High |
| 20 | `/admin/verifications` | Admin verification review queue | High |
| 21 | `/about` | About RealityNG | Medium |
| 22 | `/verification-standards` | Public verification standards | High |
| 23 | `/listing-standards` | Listing standards | Medium |
| 24 | `/safety` | Safety/trust guidance | Medium |
| 25 | `/help` | Help centre | Medium |
| 26 | `/contact` | Contact page | Medium |
| 27 | `/privacy` | Privacy policy | Low |
| 28 | `/terms` | Terms | Low |
| 29 | `/data-deletion` and `/refunds` | Legal/support policies | Low |

## 9. Design Scope To Quote

The designer should quote in phases.

### Phase A: Core Marketplace Redesign

Must include:

- Homepage.
- Required process-flow / How It Works section.
- Property browse/search results.
- Property detail.
- Services marketplace browse.
- Service provider profile.
- Responsive navbar.
- Mobile menu.
- Footer.
- Search components.
- Property cards.
- Provider cards.
- Empty/loading/error states.

Recommended design count:

- 9 core page templates.
- Desktop, tablet, and mobile versions for each critical screen.
- Component variants for cards, buttons, search, filters, badges, modals, and drawers.

### Phase B: Auth, Onboarding, and Buyer Flow

Must include:

- Sign up.
- Sign in.
- Forgot password.
- Reset password.
- Role setup.
- Saved properties.
- Rental application form.
- Profile settings.
- Account-required modal/prompt.

Recommended design count:

- 9 page templates.
- Mobile and desktop versions.
- Form validation and success/error states.

### Phase C: Supplier and Property Owner Flow

Must include:

- Add property wizard.
- Property media upload state.
- Property verification submission.
- Owner/agent dashboard states.
- Inquiries section.
- Viewing requests section.
- Applications review section.

Recommended design count:

- 7 to 10 workflow screens.
- Draft, pending, approved, rejected, and empty states.

### Phase D: Verification and Admin Operations

Must include:

- Verification centre.
- New verification request.
- Property verification request.
- Admin dashboard.
- Admin verification queue.
- Verification detail/review state.
- Approve/reject/request-more-information modal states.

Recommended design count:

- 6 to 8 page/workflow templates.
- Strong attention to document privacy, review notes, and status clarity.

### Phase E: Design System and Component Library

Must include:

- Color tokens.
- Typography scale.
- Spacing scale.
- Buttons.
- Inputs.
- Selects.
- Search tabs.
- Cards.
- Badges.
- Verification badges.
- Status badges.
- Modals.
- Drawers.
- Tables.
- Dashboard stats.
- Mobile bottom sheets.
- Skeletons.
- Empty states.
- Toasts/alerts.
- AI assistant widget.
- Map/list/split-view controls.

Recommended deliverable:

- Figma component library with variants and auto-layout.

## 10. Total Design Estimate

Minimum design scope:

- 29 current route templates.
- 15 to 25 reusable components.
- Desktop and mobile states for key pages.
- Tablet states for complex layouts.

Recommended full quote scope:

- 30 to 40 screen designs.
- 20 to 35 reusable components.
- 10 to 20 important states and modals.
- Clickable prototype for the critical user journeys.

Critical journeys to prototype:

1. Visitor searches and opens a property.
2. Visitor saves property and is prompted to sign up.
3. Buyer submits an inquiry.
4. Buyer requests a viewing.
5. Buyer submits rental application.
6. Landlord lists a property.
7. User submits verification.
8. Admin approves or rejects verification.
9. Visitor browses service providers.
10. Visitor opens a provider profile.
11. Visitor understands the full RealityNG process flow from search to dashboard tracking.

## 11. Pages That Need Highest Design Attention

Highest priority:

- Homepage.
- Homepage process flow / How It Works journey.
- Property browse/results.
- Property detail.
- Search and filters.
- Mobile navigation.
- Property card.
- Verification badges.
- Services marketplace.
- Provider profile.
- Dashboard.
- Verification centre.
- Admin verification queue.

Medium priority:

- Auth pages.
- Saved properties.
- Application form.
- Add property flow.
- Profile settings.
- Public trust/legal pages.

Lower priority:

- Static legal pages such as terms, privacy, refunds, and data deletion.

## 12. What The Design Must Achieve

The design should help RealityNG:

- Look credible enough for investors and leadership.
- Feel simple enough for first-time users.
- Make property search the main experience.
- Preserve the full RealityNG process flow from discovery to decision tracking.
- Reduce premature sign-up friction.
- Show verification clearly without overpromising.
- Make Nigerian locations and property categories easy to understand.
- Support mobile users strongly.
- Help diaspora users feel safer.
- Prepare for verified service providers and future bookings.
- Preserve all existing engineering functionality.

## 13. What The Designer Should Not Do

Do not design or add:

- Lawyer marketplace.
- Legal review workflow.
- Payments.
- Messaging.
- Full service booking workflow.
- Reviews and complaints workflow.
- Construction tracking details.
- Remote CCTV/IoT monitoring.

These are not part of the current design scope unless separately approved.

## 14. Required Designer Deliverables

The designer should deliver:

- Figma source file.
- Clickable prototype.
- Desktop designs.
- Mobile designs.
- Tablet designs for complex pages.
- Component library.
- Design tokens.
- Interaction notes.
- Empty/loading/error states.
- Responsive behavior notes.
- Developer handoff annotations.
- Exported icons/assets if new assets are introduced.
- Style guide page.
- Page-by-page notes explaining user goals and assumptions.

## 15. Handoff Requirements For Engineering

The design must include:

- Exact spacing and layout rules.
- Component variants.
- Button states.
- Input states.
- Form validation states.
- Modal behavior.
- Mobile menu behavior.
- Sticky CTA behavior.
- Image ratios.
- Card ratios.
- Accessibility notes.
- Color contrast considerations.
- Responsive breakpoints.
- Design tokens that can map to Tailwind CSS.

Preferred breakpoints:

- 320px.
- 375px.
- 430px.
- 768px.
- 1024px.
- 1366px.
- 1440px.

## 16. Suggested Design Process

Recommended workflow:

1. Product discovery call.
2. Review current RealityNG app.
3. Review existing UI/UX flows document.
4. Review Redfin only as a usability benchmark.
5. Create low-fidelity wireframes.
6. Approve information architecture.
7. Create high-fidelity homepage, browse, and detail designs first.
8. Build design system components.
9. Design remaining workflows.
10. Create mobile variants.
11. Create prototype.
12. Conduct review with leadership.
13. Revise.
14. Prepare developer handoff.

## 17. Pricing Discussion Prompt For Designer

Ask the designer to provide a quote with:

- Fixed price per phase.
- Timeline per phase.
- Number of included revision rounds.
- Whether component library is included.
- Whether mobile/tablet variants are included.
- Whether clickable prototype is included.
- Whether developer handoff is included.
- Hourly rate for additional changes.
- Payment milestones.
- File ownership terms.

Recommended quote structure:

| Phase | Scope | Designer Quote | Timeline |
| --- | --- | --- | --- |
| Phase A | Core marketplace redesign | To be quoted | To be quoted |
| Phase B | Auth, onboarding, buyer flow | To be quoted | To be quoted |
| Phase C | Supplier and owner flow | To be quoted | To be quoted |
| Phase D | Verification and admin | To be quoted | To be quoted |
| Phase E | Design system/component library | To be quoted | To be quoted |

## 18. Questions For Designer

The designer should answer:

1. Have you designed property, marketplace, SaaS, fintech, or trust-heavy products before?
2. Can you work from an existing live product and improve it without breaking the current user flow?
3. Can you provide both desktop and mobile responsive designs?
4. Can you build a reusable Figma component system?
5. Can you create developer handoff notes for Tailwind/Next.js implementation?
6. How many revisions are included?
7. What is your estimated timeline for Phase A only?
8. What is your estimated timeline for the full design package?

## 19. Success Criteria

The design engagement is successful when:

- RealityNG has a clear, polished, premium product interface.
- Public search and property discovery feel simple and powerful.
- Mobile experience feels intentional.
- Verification and trust information are easy to understand.
- The app no longer feels cluttered or inconsistent.
- Developers can implement the designs without guessing.
- The design supports current functionality and future Sprint 9 work.

## 20. Attachments To Share With Designer

Share these documents:

- `docs/RealityNG-UI-UX-Flows.md`
- `docs/RealityNG-PRD.md`
- `docs/RealityNG-Sprint-Breakdown.md`
- `docs/RealityNG-Sprint-9.1-Marketplace-Foundation-Report.md`
- Current live frontend URL.
- Screenshots of areas leadership wants improved.
- Logo assets from the frontend project.

## Final Note

RealityNG should feel like a premium Nigerian property and trust marketplace, not a generic real estate template. The goal is not decoration. The goal is clarity, confidence, conversion, and trust.
