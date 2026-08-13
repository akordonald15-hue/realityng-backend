# RealityNG Financial Partner Integration Checklist

Status: Planning only  
Use this checklist before enabling any production escrow or financing partner.

## Partner Identity

- Legal name
- Product owner
- Technical owner
- Compliance contact
- Support escalation contact
- Contract status
- Sandbox access status
- Production approval status
- Supported countries
- Supported currencies

## Escrow Partner Checklist

### Product Fit

- Licensed to custody or administer escrow funds
- Supports NGN transactions
- Supports property-related transaction values
- Supports buyer/seller references
- Supports partial release if construction milestones require it
- Supports refunds
- Supports dispute holds
- Supports reconciliation exports or APIs
- Provides settlement confirmations

### API And Webhooks

- Sandbox API documentation received
- Production API documentation received
- Webhook event catalogue received
- Webhook signature method documented
- Idempotency support documented
- Rate limits documented
- Retry behavior documented
- Error codes documented
- Reconciliation endpoint/export available
- UAT credentials issued
- Production credentials issued through secure channel

### Operational Policy

- Funding confirmation rules
- Release instruction rules
- Refund instruction rules
- Dispute hold rules
- Settlement timing
- Failed settlement handling
- Manual override process
- Reversal process
- Support SLA

### Compliance

- Contract signed
- Data processing terms signed
- NDPR/data privacy review complete
- AML/KYC obligations defined
- Customer terms approved
- Fee disclosure approved
- Dispute policy approved

## Financing Partner Checklist

### Product Fit

- Supports rent finance and/or mortgage prequalification
- Supports target customer types
- Supports target states/cities
- Provides eligibility criteria
- Provides document requirements
- Provides decision SLA
- Provides partner-owned offer terms
- Provides status callbacks or reporting

### Data Requirements

- Applicant identity fields
- Employment/income fields
- Property fields
- Required documents
- Consent language
- Retention rules
- Rejection reason policy
- Offer display rules

### Integration

- Manual submission process approved
- API submission process documented
- Webhook status events documented
- Partner reference format documented
- Idempotency support documented
- Retry/error handling documented
- Sandbox tested
- Production credentials securely issued

## Security Review

- Secrets stored outside repository
- Secrets unavailable to frontend
- API key rotation process documented
- Webhook signature test completed
- IP allow-list requirement documented where applicable
- Audit log requirements documented
- Partner payload minimization agreed
- Incident response path documented

## RealityNG Readiness

- Environment variables documented
- Admin runbook updated
- Rollback process documented
- Reconciliation process documented
- Monitoring alerts defined
- Smoke test checklist written
- Support scripts reviewed
- Legal copy approved
- User-facing status copy approved

## Go/No-Go Questions

Do not activate production until all answers are yes:

- Is the partner legally approved?
- Are production credentials issued securely?
- Has sandbox integration passed?
- Are webhook signatures verified?
- Are reconciliation procedures tested?
- Are customer terms approved?
- Are rollback and manual support paths documented?
- Has a production smoke test plan been approved?

