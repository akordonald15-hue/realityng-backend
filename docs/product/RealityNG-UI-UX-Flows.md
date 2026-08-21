# RealityNG UI/UX Flows

Version: 1.0  
Date: 2026-06-16  
Source: RealityNG PRD v1.0

## 1. UX System Principles

1. Trust signals must be visible at decision points: listing card, property detail, professional profile, payment milestone, and admin queue.
2. Every high-risk workflow should show status, owner, next action, and evidence requirements.
3. Diaspora users need confidence, not clutter: prioritize verification, legal, inspection, and progress timelines.
4. Dashboards should be task-driven with queues, pending actions, and recent updates.
5. Forms should save drafts where workflows are long or document-heavy.

## 2. Complete Web App Page Structure

Public:

1. `/` Home.
2. `/properties` Browse listings.
3. `/properties/[id]` Property detail.
4. `/artisans` Find artisans.
5. `/artisans/[id]` Artisan detail.
6. `/compare` Property comparison.

Auth and onboarding:

1. `/auth/sign-up`.
2. `/auth/sign-in`.
3. `/auth/verify-email`.
4. `/auth/verify-phone`.
5. `/auth/forgot-password`.
6. `/onboarding/role-setup`.
7. `/onboarding/profile`.

Dashboards:

1. `/dashboard` Role-aware dashboard landing.
2. `/dashboard/tenant`.
3. `/dashboard/buyer`.
4. `/dashboard/landlord`.
5. `/dashboard/agent`.
6. `/dashboard/artisan`.
7. `/dashboard/lawyer`.
8. `/dashboard/inspector`.
9. `/dashboard/admin`.

Workflow pages:

1. `/properties/new`.
2. `/properties/[id]/edit`.
3. `/properties/[id]/apply`.
4. `/viewings`.
5. `/applications`.
6. `/favorites`.
7. `/saved-searches`.
8. `/verification-requests`.
9. `/legal-reviews`.
10. `/inspection-requests`.
11. `/inspection-reports/[id]`.
12. `/service-bookings`.
13. `/construction-projects`.
14. `/construction-projects/[id]`.
15. `/payment-milestones`.
16. `/disputes`.
17. `/notifications`.
18. `/settings/profile`.
19. `/settings/security`.

Admin:

1. `/admin`.
2. `/admin/users`.
3. `/admin/properties`.
4. `/admin/approvals`.
5. `/admin/verification`.
6. `/admin/legal-reviews`.
7. `/admin/inspections`.
8. `/admin/artisans`.
9. `/admin/payments`.
10. `/admin/disputes`.
11. `/admin/audit-logs`.
12. `/admin/system-health`.

## 3. Dashboard Structure

Tenant dashboard:

1. Upcoming viewings.
2. Active applications.
3. Favorites.
4. Saved searches.
5. Notifications.

Buyer/diaspora dashboard:

1. Saved properties.
2. Verification/legal/inspection requests.
3. Payment milestones.
4. Construction projects.
5. Disputes and support.

Landlord dashboard:

1. Listing inventory.
2. Viewing requests.
3. Applications.
4. Verification status.
5. Listing performance.

Agent dashboard:

1. Listings.
2. Leads/viewings.
3. Applications.
4. CAC/verification status.
5. Performance and response SLA.

Artisan dashboard:

1. Profile completion.
2. Booking requests.
3. Quotes/schedule.
4. Reviews.
5. Verification status.

Lawyer dashboard:

1. Assigned legal reviews.
2. Awaiting documents.
3. Draft opinions.
4. SLA alerts.

Inspector dashboard:

1. Assigned inspections.
2. Schedule.
3. Draft reports.
4. Released reports.
5. SLA alerts.

Admin dashboard:

1. Approval queues.
2. Assignment queues.
3. Disputes.
4. Payment proof review.
5. Audit log search.
6. System health.

## 4. Flow Specifications

### 4.1 Guest Browsing Flow

Entry Point: Home page, shared property link, search engine listing.  
Screens: Home, browse listings, map/list view, property detail, compare, sign-up modal/page.  
User Actions:

1. Enters location/category/price filters.
2. Sorts and filters listings.
3. Opens property detail.
4. Compares properties.
5. Attempts favorite, book viewing, request inspection, or apply.

System Responses:

1. Returns public listing results.
2. Shows public trust badges.
3. Redacts sensitive address/documents.
4. Prompts sign-in for saved or transactional actions.

Empty States:

1. No listings match filters: show broaden-filter actions and save-search prompt.
2. Map area empty: allow search nearby or clear bounds.

Error States:

1. Invalid filters: inline validation.
2. Map provider unavailable: fallback to list view.
3. Listing removed: show unavailable state and similar listings.

Success States:

1. Search results loaded.
2. Property added to comparison.
3. Sign-up redirect preserves intended action.

Required API Calls:

1. `GET /api/v1/properties/`
2. `GET /api/v1/properties/{id}/`
3. `GET /api/v1/comparisons/preview/`

Required UI Components:

Search bar, filter panel, listing card, map, property media gallery, trust badge, comparison drawer, sign-in prompt.

### 4.2 Tenant Registration and Application Flow

Entry Point: Apply CTA on rental property or sign-up page.  
Screens: Sign up, role setup, profile, property detail, application form, document upload, application status.  
User Actions:

1. Registers or signs in.
2. Selects tenant role.
3. Completes profile and verifies email/phone.
4. Opens rental property.
5. Starts application.
6. Completes required answers and uploads documents.
7. Submits application.

System Responses:

1. Creates user and tenant role.
2. Saves application draft.
3. Validates required fields.
4. Notifies landlord/agent on submission.
5. Shows status timeline.

Empty States:

1. No applications: show browse listings CTA.
2. No required documents uploaded: show checklist.

Error States:

1. Phone not verified: block submission and send OTP.
2. Property unavailable: prevent submission.
3. Duplicate active application: show existing application.

Success States:

1. Application submitted.
2. Status is visible in tenant dashboard.

Required API Calls:

1. `POST /api/v1/auth/register/`
2. `POST /api/v1/roles/request/`
3. `PATCH /api/v1/users/me/`
4. `POST /api/v1/applications/`
5. `POST /api/v1/documents/upload-intents/`
6. `POST /api/v1/documents/{id}/complete/`

Required UI Components:

Auth forms, role selector, profile form, application wizard, document uploader, status timeline, application summary.

### 4.3 Diaspora Buyer Property Purchase Confidence Flow

Entry Point: Sale or land property detail.  
Screens: Property detail, comparison, buyer dashboard, verification request, inspection request, legal review request, document vault, payment milestone tracker.  
User Actions:

1. Saves and compares properties.
2. Reviews trust badges and owner/agent status.
3. Requests property verification.
4. Requests inspection.
5. Requests legal review.
6. Uploads or requests documents.
7. Reviews inspection report and legal opinion.
8. Tracks payment milestones.

System Responses:

1. Creates trust workflow records.
2. Shows required evidence checklist.
3. Sends admin assignment queue items.
4. Releases reports/opinions after QA.
5. Updates buyer dashboard status.

Empty States:

1. No trust requests yet: show recommended next actions.
2. No documents: show document request CTA.

Error States:

1. Property not eligible: show reason.
2. Legal review needs more documents: show missing document checklist.
3. Inspection rejected: show recommendation and next actions.

Success States:

1. Verification status updated.
2. Inspection report released.
3. Legal opinion issued.
4. Payment milestone approved or disputed.

Required API Calls:

1. `POST /api/v1/favorites/`
2. `POST /api/v1/verification-requests/`
3. `POST /api/v1/inspection-requests/`
4. `POST /api/v1/legal-reviews/`
5. `GET /api/v1/inspection-reports/{id}`
6. `GET /api/v1/payment-milestones/`

Required UI Components:

Trust panel, confidence checklist, request cards, document uploader, report viewer, opinion viewer, milestone timeline.

### 4.4 Landlord Listing Flow

Entry Point: Landlord dashboard or add listing CTA.  
Screens: Role setup, landlord dashboard, add listing wizard, media upload, document upload, preview, submission confirmation.  
User Actions:

1. Selects landlord role.
2. Creates listing draft.
3. Enters property facts and location.
4. Uploads media.
5. Uploads ownership/authorization documents if requested.
6. Previews listing.
7. Submits for approval.

System Responses:

1. Saves draft after each step.
2. Validates category-specific fields.
3. Geocodes address.
4. Sends listing to admin queue.
5. Notifies landlord of approval/rejection.

Empty States:

1. No listings: show create listing CTA.
2. No media: show required media checklist.

Error States:

1. Missing required fields.
2. Geocoding failure: allow manual location confirmation.
3. Submission blocked by unverified contact.

Success States:

1. Listing submitted.
2. Listing approved and published.

Required API Calls:

1. `POST /api/v1/properties/`
2. `PATCH /api/v1/properties/{id}/`
3. `POST /api/v1/documents/upload-intents/`
4. `POST /api/v1/properties/{id}/media/`
5. `POST /api/v1/properties/{id}/submit/`

Required UI Components:

Listing wizard, address picker/map, media uploader, document uploader, preview card, submission checklist.

### 4.5 Agent Onboarding and CAC Verification Flow

Entry Point: Role setup or agent dashboard.  
Screens: Role setup, agent profile, CAC upload, verification request, agent dashboard.  
User Actions:

1. Requests agent role.
2. Completes business/profile details.
3. Uploads CAC or business credential.
4. Submits verification request.
5. Waits for approval or responds to more-info request.

System Responses:

1. Creates pending agent role.
2. Stores documents securely.
3. Creates verification request.
4. Admin approves/rejects.
5. Activates agent capabilities after approval.

Empty States:

1. No CAC uploaded: show upload task.
2. No listings: show create listing once approved.

Error States:

1. Invalid file type.
2. Duplicate role request.
3. Verification rejected: show reason and resubmit option if allowed.

Success States:

1. Agent role active.
2. Verification badge visible.

Required API Calls:

1. `POST /api/v1/roles/request/`
2. `PATCH /api/v1/users/me/`
3. `POST /api/v1/documents/upload-intents/`
4. `POST /api/v1/verification-requests/`

Required UI Components:

Role request card, business profile form, CAC upload field, verification status badge, task checklist.

### 4.6 Artisan Onboarding and Booking Flow

Entry Point: Role setup or artisan directory booking CTA.  
Screens: Artisan onboarding, profile editor, portfolio upload, artisan detail, booking request, booking dashboard.  
User Actions:

1. Artisan creates profile.
2. Uploads portfolio and service locations.
3. Submits profile for approval.
4. Customer browses and requests booking.
5. Artisan quotes or accepts.
6. Booking is scheduled and completed.
7. Customer reviews completed booking.

System Responses:

1. Hides unapproved profile from public directory.
2. Sends approval queue item.
3. Notifies artisan of booking request.
4. Enforces booking status transitions.
5. Allows review after completion.

Empty States:

1. No portfolio: show upload prompt.
2. No bookings: show availability/profile completion prompt.

Error States:

1. Artisan unavailable.
2. Booking transition invalid.
3. Review attempted before completion.

Success States:

1. Profile approved.
2. Booking scheduled/completed.
3. Review published.

Required API Calls:

1. `POST /api/v1/artisans/`
2. `POST /api/v1/artisans/{id}/submit/`
3. `POST /api/v1/service-bookings/`
4. `PATCH /api/v1/service-bookings/{id}/`
5. `POST /api/v1/reviews/`

Required UI Components:

Artisan profile form, portfolio uploader, directory filters, booking form, quote card, review form.

### 4.7 Lawyer Legal Review Flow

Entry Point: Lawyer dashboard assignment.  
Screens: Lawyer dashboard, legal review detail, document viewer, request more info modal, opinion editor.  
User Actions:

1. Opens assigned legal review.
2. Reviews property and documents.
3. Requests additional documents if needed.
4. Drafts legal opinion.
5. Issues final opinion.

System Responses:

1. Shows assigned-only reviews.
2. Logs sensitive document access.
3. Notifies requester for missing documents.
4. Locks final opinion as versioned record.

Empty States:

1. No assignments: show empty queue.
2. No documents: show request-documents action.

Error States:

1. Unauthorized review access.
2. Missing required opinion fields.
3. Conflict of interest flag blocks submission.

Success States:

1. Opinion issued.
2. Requester notified.

Required API Calls:

1. `GET /api/v1/legal-reviews/`
2. `GET /api/v1/documents/{id}/download-url/`
3. `PATCH /api/v1/legal-reviews/{id}/`
4. `POST /api/v1/legal-reviews/{id}/opinion/`

Required UI Components:

Assignment table, document list, secure viewer, opinion editor, risk selector, status timeline.

### 4.8 Inspector Inspection Report Flow

Entry Point: Inspector dashboard assignment.  
Screens: Inspector dashboard, inspection detail, schedule view, report form, media uploader, submitted report.  
User Actions:

1. Opens assigned inspection.
2. Confirms schedule.
3. Captures or uploads photos/videos.
4. Completes checklist and recommendation.
5. Submits report.

System Responses:

1. Shows inspection scope and location.
2. Requires evidence before submission.
3. Stores metadata and files securely.
4. Sends report to admin QA.

Empty States:

1. No assigned inspections.
2. No uploaded evidence: show evidence checklist.

Error States:

1. Missing checklist item.
2. Upload failure.
3. Inspection already submitted.

Success States:

1. Report submitted for QA.
2. Admin releases report.

Required API Calls:

1. `GET /api/v1/inspection-requests/`
2. `PATCH /api/v1/inspection-requests/{id}/`
3. `POST /api/v1/documents/upload-intents/`
4. `POST /api/v1/inspection-reports/`

Required UI Components:

Inspection queue, schedule card, checklist form, recommendation selector, media uploader, report preview.

### 4.9 Admin Approval and Assignment Flow

Entry Point: Admin dashboard queue card.  
Screens: Admin dashboard, approval queue, entity review detail, assignment modal, decision modal, audit trail.  
User Actions:

1. Opens queue.
2. Filters by entity/status/priority.
3. Reviews submitted data and documents.
4. Assigns specialist where required.
5. Approves, rejects, requests more info, or suspends.

System Responses:

1. Applies permission checks.
2. Writes audit log for decisions.
3. Notifies affected users.
4. Updates public badges/status where applicable.

Empty States:

1. Queue empty: show last processed timestamp.

Error States:

1. Invalid transition.
2. Missing decision reason.
3. Assignee unavailable or unapproved.

Success States:

1. Entity status updated.
2. Assignment created.
3. Audit log visible.

Required API Calls:

1. `GET /api/v1/admin/dashboard/`
2. `GET /api/v1/admin/approvals/`
3. `POST /api/v1/admin/assignments/`
4. Decision endpoints per workflow.
5. `GET /api/v1/admin/audit-logs/`

Required UI Components:

Queue table, filters, detail drawer, document viewer, assignment modal, decision form, audit timeline.

### 4.10 Construction Project Tracking Flow

Entry Point: Buyer dashboard or property ownership workflow.  
Screens: Project list, create project, project detail, milestone board, milestone detail, inspection request, report view.  
User Actions:

1. Creates project.
2. Adds or accepts default milestones.
3. Uploads project documents.
4. Updates milestone progress.
5. Requests inspection for milestone.
6. Reviews inspection report.
7. Approves or disputes milestone.

System Responses:

1. Creates project and milestone records.
2. Connects inspection requests to milestones.
3. Updates progress timeline.
4. Locks payment recommendation until approval.

Empty States:

1. No projects: show create project CTA.
2. No milestones: show apply template action.

Error States:

1. Milestone approval attempted without report.
2. Invalid progress percentage.
3. Project archived or disputed.

Success States:

1. Milestone approved.
2. Project progress updated.

Required API Calls:

1. `POST /api/v1/construction-projects/`
2. `POST /api/v1/project-milestones/`
3. `PATCH /api/v1/project-milestones/{id}/`
4. `POST /api/v1/project-milestones/{id}/submit-inspection/`
5. `POST /api/v1/inspection-requests/`

Required UI Components:

Project form, milestone board, progress bar, document uploader, inspection CTA, report viewer.

### 4.11 Payment Milestone Tracking Flow

Entry Point: Project milestone, legal review, inspection request, service booking, or buyer dashboard.  
Screens: Payment milestone list, milestone detail, proof upload, admin proof review, event history.  
User Actions:

1. Creates or views payment milestone.
2. Uploads proof of external payment.
3. Tracks review state.
4. Admin approves/rejects proof.
5. User disputes if needed.

System Responses:

1. Records payment milestone.
2. Stores proof as private document.
3. Appends payment event.
4. Locks disputed milestones.
5. Shows external payment disclaimer.

Empty States:

1. No milestones: show create milestone where authorized.

Error States:

1. Proof uploaded by unauthorized user.
2. Payment already approved.
3. Milestone disputed.

Success States:

1. Proof uploaded.
2. Payment marked approved or rejected.

Required API Calls:

1. `POST /api/v1/payment-milestones/`
2. `POST /api/v1/documents/upload-intents/`
3. `POST /api/v1/payment-milestones/{id}/proof/`
4. `POST /api/v1/admin/payment-milestones/{id}/decision/`

Required UI Components:

Milestone table, status badge, external payment disclaimer, proof uploader, event timeline, dispute CTA.

### 4.12 Dispute Reporting Flow

Entry Point: Report listing CTA, payment milestone detail, booking detail, inspection/legal review detail.  
Screens: Dispute form, evidence upload, dispute detail, admin dispute queue, resolution view.  
User Actions:

1. Selects dispute category.
2. Describes issue.
3. Uploads evidence.
4. Submits dispute.
5. Responds to admin requests.
6. Views resolution.

System Responses:

1. Creates dispute case.
2. Locks related workflow if required.
3. Notifies respondent/admin.
4. Tracks admin actions and resolution.

Empty States:

1. No disputes: show support and safety guidance.

Error States:

1. User not a participant in related entity.
2. Missing description.
3. Duplicate open dispute.

Success States:

1. Dispute opened.
2. Resolution published.

Required API Calls:

1. `POST /api/v1/disputes/`
2. `PATCH /api/v1/disputes/{id}/`
3. `POST /api/v1/documents/upload-intents/`
4. `POST /api/v1/admin/disputes/{id}/resolve/`

Required UI Components:

Dispute category selector, evidence uploader, case timeline, participant response form, admin resolution panel.

