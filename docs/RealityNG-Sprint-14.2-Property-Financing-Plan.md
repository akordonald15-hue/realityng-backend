# RealityNG Sprint 14.2 Property Financing Plan

Status: Planning only  
Dependency: Sprint 14.1 escrow architecture should be stable before production financing handoff is activated.

## Executive Summary

Sprint 14.2 should introduce a financing marketplace layer for rent finance and mortgage prequalification. RealityNG should not act as the lender, credit bureau, or underwriter in the MVP. RealityNG should collect user consent, structure application data, manage document upload, submit to approved financial partners, and display partner-owned decisions safely.

Financing must remain separate from escrow. Escrow handles custody and release of transaction funds. Financing handles eligibility, underwriting, offers, acceptance, and partner disbursement decisions.

## Product Scope

Supported MVP flows:

- rent financing enquiry/application
- mortgage prequalification enquiry/application
- partner offer display
- application document checklist
- status tracking
- admin review and partner handoff

Out of scope:

- RealityNG lending balance sheet
- credit scoring engine
- automated loan approval
- payment collections
- repayment schedules
- default management
- insurance underwriting

## Domain Model Plan

### FinancingPartner

Suggested fields:

- `name`
- `slug`
- `status`
- `partner_type`: `bank`, `fintech`, `mortgage_bank`, `cooperative`, `manual`
- `integration_mode`: `manual`, `api`, `hybrid`
- `supported_products`
- `supported_states`
- `minimum_amount`
- `maximum_amount`
- `contact_policy`
- `created_at`
- `updated_at`

Do not store partner API secrets in the database.

### FinancingProduct

Suggested fields:

- `partner`
- `name`
- `product_type`: `rent_finance`, `mortgage`, `construction_finance`
- `status`
- `currency`
- `minimum_amount`
- `maximum_amount`
- `minimum_tenor_months`
- `maximum_tenor_months`
- `requires_property`
- `requires_income_documents`
- `requires_identity_verification`
- `requires_bank_statement`
- `created_at`
- `updated_at`

### FinancingApplication

Suggested fields:

- `applicant`
- `property`
- `transaction`
- `product`
- `partner`
- `application_reference`
- `status`
- `requested_amount`
- `currency`
- `purpose`
- `preferred_tenor_months`
- `employment_status`
- `monthly_income_band`
- `state`
- `city`
- `consent_status`
- `submitted_at`
- `partner_submitted_at`
- `decision_at`
- `created_at`
- `updated_at`

Recommended statuses:

- `draft`
- `submitted`
- `under_review`
- `partner_review`
- `more_information_requested`
- `offer_received`
- `offer_accepted`
- `offer_declined`
- `rejected`
- `cancelled`
- `expired`

### FinancingConsent

Records explicit permission to share applicant data with partners.

Suggested fields:

- `application`
- `applicant`
- `scope`
- `accepted_terms_version`
- `consented_at`
- `revoked_at`
- `ip_address`
- `user_agent`

Consent is required before partner submission.

### FinancingDocumentRequirement

Configurable requirement per product or partner.

Suggested fields:

- `product`
- `document_type`
- `required`
- `description`
- `allowed_mime_types`
- `max_size_mb`
- `created_at`

### FinancingDocument

Private uploaded document.

Suggested fields:

- `application`
- `uploaded_by`
- `document_type`
- `object_key`
- `original_filename`
- `mime_type`
- `file_size`
- `status`
- `reviewed_by`
- `reviewed_at`
- `created_at`

Use private storage and signed URLs. Do not reuse public property-media buckets.

### FinancingPartnerSubmission

Tracks a submission attempt to a partner.

Suggested fields:

- `application`
- `partner`
- `submission_reference`
- `status`
- `submitted_at`
- `response_received_at`
- `payload_hash`
- `error_message`
- `retry_count`
- `created_at`

### FinancingOffer

Partner-owned offer terms.

Suggested fields:

- `application`
- `partner`
- `offer_reference`
- `status`
- `approved_amount`
- `currency`
- `tenor_months`
- `interest_rate_display`
- `fees_display`
- `monthly_payment_display`
- `expires_at`
- `created_at`
- `updated_at`

Do not calculate legally binding APR unless the partner provides approved values.

### FinancingTimelineEvent

Append-only application history.

Suggested fields:

- `application`
- `actor`
- `event_type`
- `message`
- `visibility`: `internal`, `applicant`, `partner`
- `created_at`

## API Surface

| Endpoint | Purpose | Auth |
| --- | --- | --- |
| `GET /api/v1/financing/products/` | public product list | public |
| `POST /api/v1/financing/applications/` | create draft/application | authenticated |
| `GET /api/v1/financing/applications/my/` | applicant applications | applicant |
| `GET /api/v1/financing/applications/{id}/` | application detail | applicant/admin |
| `PATCH /api/v1/financing/applications/{id}/` | update draft fields | applicant while draft/more-info |
| `POST /api/v1/financing/applications/{id}/submit/` | submit for review | applicant |
| `POST /api/v1/financing/applications/{id}/consent/` | grant data-sharing consent | applicant |
| `POST /api/v1/financing/applications/{id}/documents/` | upload document | applicant |
| `GET /api/v1/financing/applications/{id}/documents/{doc_id}/signed-url/` | short-lived access | applicant/admin |
| `GET /api/v1/financing/applications/{id}/offers/` | offers | applicant/admin |
| `POST /api/v1/financing/offers/{id}/accept/` | accept offer | applicant |
| `POST /api/v1/financing/offers/{id}/decline/` | decline offer | applicant |
| `GET /api/v1/financing/admin/applications/` | admin queue | admin |
| `POST /api/v1/financing/admin/applications/{id}/submit-to-partner/` | partner handoff | admin/system |
| `POST /api/v1/financing/webhooks/{partner_slug}/` | partner events | signed partner requests |

## Privacy And Compliance

Financing data is more sensitive than ordinary marketplace data. Treat it as private financial information.

Requirements:

- explicit applicant consent before partner submission
- private document storage
- short-lived signed document access
- strict applicant/admin authorization
- no public display of application or credit status
- no applicant data in frontend environment variables
- no raw partner payloads in public serializers
- audit events for submission, consent, document access, decision, and offer acceptance

## Partner Integration Modes

### Manual

RealityNG admin reviews an application and exports/submits to partner through an approved off-platform process. This is safest for MVP.

### API

RealityNG sends application data and receives status/offer webhooks through a partner adapter. Use only after sandbox certification.

### Hybrid

Application starts manually, then partner webhooks update the status.

## Validation Rules

- Applicant must be authenticated.
- Consent must exist before partner submission.
- Required documents must be uploaded before final submission.
- Application amount must fit selected product limits.
- Product and partner must be active.
- Application cannot be submitted to partner twice without idempotency.
- Applicant cannot modify submitted underwriting fields unless status allows more information.
- Admin-only internal notes must not be visible to applicants.

## Frontend Dependencies

- product discovery and eligibility copy
- financing application form
- document checklist
- consent screen
- applicant status tracker
- offer cards
- admin queue

## Test Plan

Backend tests:

- application ownership
- draft update rules
- required document validation
- consent enforcement
- partner submission idempotency
- private document signed URL access
- cross-user IDOR denial
- partner webhook signature rejection
- offer accept/decline rules
- admin-only queue
- audit events

## Open Questions

- Which financing partners are approved?
- What exact applicant fields may be collected?
- Are bank statements allowed to be uploaded to RealityNG?
- Does RealityNG need NDPR/Data Protection Impact Assessment before launch?
- What consent text is legally approved?
- Can RealityNG display estimated rates, or only partner-provided offers?
- What is the SLA for partner decisions?
- Are rejected applications retained, and for how long?

## Recommended Build Order

1. Financing partner/product read models.
2. Applicant draft application.
3. Consent and document upload.
4. Admin review queue.
5. Manual partner submission.
6. Offer display and applicant response.
7. Partner API/webhooks after contracts and sandbox access.

