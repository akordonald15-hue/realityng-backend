# RealityNG ERD Specification

Version: 1.0  
Date: 2026-06-16  
Source: RealityNG PRD v1.0

## 1. Design Conventions

1. Primary keys use UUID.
2. Timestamps: `created_at`, `updated_at` on all mutable entities.
3. Soft delete: `deleted_at` on user-facing or operational records where deletion must preserve auditability.
4. Money fields use `amount_minor` as integer plus `currency` char(3), unless decimal is explicitly required for reporting.
5. Status fields are strings constrained by application enums and database checks where practical.
6. File binaries live in object storage. Database stores document metadata and storage keys.
7. Geospatial data uses PostGIS `geography(Point, 4326)` for `Property.location_point`.
8. All admin decisions and sensitive status transitions write to `AuditLog`.

## 2. Text-Based ERD Relationship Diagram

```text
User 1--1 UserProfile
User 1--* UserRole *--1 Role
User 1--* Property(owner)
User 1--* Property(agent)
Property 1--* PropertyMedia
Property 1--* PropertyDocument
Property 1--* Application
Property 1--* Viewing
Property 1--* Favorite
User 1--* Favorite
User 1--* SavedSearch
User 1--0..1 Artisan
Artisan 1--* ServiceBooking
User 1--* ServiceBooking(customer)
Property 0..1--* ServiceBooking
VerificationRequest *--1 User(requester)
LegalReview *--1 Property
LegalReview *--1 User(requester)
LegalReview *--0..1 User(lawyer)
InspectionRequest *--0..1 Property
InspectionRequest *--0..1 ConstructionProject
InspectionRequest *--1 User(requester)
InspectionRequest *--0..1 User(inspector)
InspectionRequest 1--* InspectionReport
ConstructionProject *--1 User(owner)
ConstructionProject 0..*--0..1 Property
ConstructionProject 1--* ProjectMilestone
ProjectMilestone 1--* PaymentMilestone
PaymentMilestone *--1 User(payer)
PaymentMilestone *--1 User(payee)
PaymentMilestone 1--* PaymentEvent
WebhookEvent 0..*--0..1 PaymentEvent
Document *--1 User(uploader)
Dispute *--1 User(complainant)
Dispute *--0..1 User(respondent)
Notification *--1 User
MessageThread 1--* Message
Message *--1 User(sender)
Review *--1 User(author)
AuditLog *--0..1 User(actor)
```

## 3. Entity Specifications

### 3.1 User

Purpose: Platform account for all user types.  
Primary Key: `id uuid`.  
Important Fields:

| Field | Type | Notes |
| --- | --- | --- |
| email | varchar(255) | Unique, nullable only if phone-first registration is enabled. |
| phone | varchar(32) | Unique where present, normalized E.164 where possible. |
| password_hash | varchar(255) | Django password hash. |
| status | varchar(32) | active, pending_verification, restricted, suspended, deleted. |
| email_verified_at | timestamptz | Null until verified. |
| phone_verified_at | timestamptz | Null until verified. |
| last_login_at | timestamptz | For risk and support. |
| deleted_at | timestamptz | Soft delete. |

Foreign Keys: none.  
Relationships: one UserProfile, many UserRole, properties, applications, viewings, favorites, saved searches, documents, notifications, audit logs.  
Indexes: unique lower(email), unique phone, status, created_at.  
Unique Constraints: email, phone.  
Soft Delete: yes.

### 3.2 Role

Purpose: Defines platform roles.  
Primary Key: `id uuid`.  
Fields: `code varchar(64)`, `name varchar(128)`, `description text`, `is_admin_role boolean`, `created_at`, `updated_at`.  
Foreign Keys: none.  
Relationships: many UserRole.  
Indexes: code.  
Unique Constraints: code.  
Status Values: active/inactive can be added if role catalog becomes editable.  
Soft Delete: no.

### 3.3 UserRole

Purpose: Assigns one or more roles to users.  
Primary Key: `id uuid`.  
Fields: `user_id uuid`, `role_id uuid`, `status varchar(32)`, `approved_by_id uuid`, `approved_at timestamptz`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: user, role, approved_by user.  
Relationships: belongs to User and Role.  
Indexes: user_id, role_id, status.  
Unique Constraints: `(user_id, role_id)` where deleted_at is null.  
Status Values: pending, active, rejected, suspended, revoked.  
Soft Delete: yes.

### 3.4 UserProfile

Purpose: Stores personal/business profile data not needed for authentication.  
Primary Key: `id uuid`.  
Fields: `user_id uuid`, `first_name varchar(100)`, `last_name varchar(100)`, `display_name varchar(160)`, `country varchar(80)`, `state varchar(80)`, `city varchar(120)`, `avatar_document_id uuid`, `identity_verification_status varchar(32)`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: user, avatar document.  
Relationships: belongs to User.  
Indexes: user_id, identity_verification_status.  
Unique Constraints: user_id.  
Status Values: not_started, submitted, verified, rejected, expired, revoked.  
Soft Delete: yes.

### 3.5 Property

Purpose: Public or private property asset/listing.  
Primary Key: `id uuid`.  
Fields: `owner_id uuid`, `agent_id uuid`, `category varchar(32)`, `property_type varchar(64)`, `status varchar(32)`, `title varchar(180)`, `description text`, `price_minor bigint`, `currency char(3)`, `state varchar(80)`, `lga varchar(120)`, `city varchar(120)`, `neighborhood varchar(160)`, `address_line text`, `location_point geography(Point,4326)`, `bedrooms smallint`, `bathrooms smallint`, `toilets smallint`, `land_size_sqm numeric(12,2)`, `building_size_sqm numeric(12,2)`, `verification_status varchar(32)`, `published_at timestamptz`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: owner user, agent user.  
Relationships: has media, documents, applications, viewings, favorites, legal reviews, inspections, verification requests.  
Indexes: status, category, price_minor, state/lga/city, verification_status, published_at, GIST location_point, owner_id, agent_id.  
Unique Constraints: none initially; duplicate detection is probabilistic.  
Status Values: draft, submitted, needs_edits, approved, published, paused, rejected, suspended, archived.  
Soft Delete: yes.

### 3.6 PropertyMedia

Purpose: Public media gallery for a property.  
Primary Key: `id uuid`.  
Fields: `property_id uuid`, `document_id uuid`, `media_type varchar(32)`, `sort_order int`, `caption varchar(255)`, `is_cover boolean`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: property, document.  
Relationships: belongs to Property and Document.  
Indexes: property_id, sort_order, is_cover.  
Unique Constraints: one cover per property enforced by partial unique index.  
Status Values: image, video, virtual_tour, floor_plan.  
Soft Delete: yes.

### 3.7 PropertyDocument

Purpose: Private or restricted property-related documents.  
Primary Key: `id uuid`.  
Fields: `property_id uuid`, `document_id uuid`, `document_type varchar(64)`, `visibility varchar(32)`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: property, document.  
Relationships: belongs to Property and Document.  
Indexes: property_id, document_type, visibility.  
Unique Constraints: none.  
Status Values: title, survey, deed, receipt, cac, lease, other.  
Soft Delete: yes.

### 3.8 Application

Purpose: Rental application submitted by a tenant.  
Primary Key: `id uuid`.  
Fields: `property_id uuid`, `applicant_id uuid`, `status varchar(32)`, `answers_json jsonb`, `submitted_at timestamptz`, `decision_at timestamptz`, `decision_by_id uuid`, `decision_reason text`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: property, applicant user, decision_by user.  
Relationships: belongs to Property and User; may have documents through Document entity association.  
Indexes: property_id, applicant_id, status, submitted_at.  
Unique Constraints: one active application per applicant/property where status not in withdrawn/rejected/deleted.  
Status Values: draft, submitted, under_review, shortlisted, approved, rejected, withdrawn.  
Soft Delete: yes.

### 3.9 Viewing

Purpose: Property viewing booking.  
Primary Key: `id uuid`.  
Fields: `property_id uuid`, `requester_id uuid`, `host_id uuid`, `status varchar(32)`, `preferred_slots_json jsonb`, `scheduled_at timestamptz`, `meeting_type varchar(32)`, `notes text`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: property, requester user, host user.  
Relationships: belongs to Property and User.  
Indexes: property_id, requester_id, host_id, status, scheduled_at.  
Unique Constraints: none.  
Status Values: requested, accepted, rescheduled, completed, no_show, cancelled.  
Soft Delete: yes.

### 3.10 Favorite

Purpose: User-saved property.  
Primary Key: `id uuid`.  
Fields: `user_id uuid`, `property_id uuid`, `created_at`, `deleted_at`.  
Foreign Keys: user, property.  
Relationships: belongs to User and Property.  
Indexes: user_id, property_id.  
Unique Constraints: `(user_id, property_id)` where deleted_at is null.  
Status Values: none.  
Soft Delete: yes.

### 3.11 SavedSearch

Purpose: Persisted search criteria and alert settings.  
Primary Key: `id uuid`.  
Fields: `user_id uuid`, `name varchar(120)`, `filters_json jsonb`, `alert_frequency varchar(32)`, `is_active boolean`, `last_notified_at timestamptz`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: user.  
Relationships: belongs to User.  
Indexes: user_id, is_active, alert_frequency.  
Unique Constraints: optional `(user_id, name)` where deleted_at is null.  
Status Values: alert_frequency none, instant, daily, weekly.  
Soft Delete: yes.

### 3.12 Artisan

Purpose: Verified service provider profile.  
Primary Key: `id uuid`.  
Fields: `user_id uuid`, `business_name varchar(180)`, `category varchar(80)`, `specializations_json jsonb`, `service_locations_json jsonb`, `years_experience smallint`, `verification_status varchar(32)`, `profile_status varchar(32)`, `rating_avg numeric(3,2)`, `rating_count int`, `bio text`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: user.  
Relationships: belongs to User; has service bookings and reviews.  
Indexes: user_id, category, verification_status, profile_status, rating_avg.  
Unique Constraints: user_id where deleted_at is null.  
Status Values: profile draft, submitted, approved, suspended, archived; verification not_requested, submitted, verified, rejected, expired, revoked.  
Soft Delete: yes.

### 3.13 ServiceBooking

Purpose: Customer request for artisan/vendor work.  
Primary Key: `id uuid`.  
Fields: `artisan_id uuid`, `customer_id uuid`, `property_id uuid`, `status varchar(32)`, `service_category varchar(80)`, `description text`, `preferred_slots_json jsonb`, `scheduled_at timestamptz`, `quote_amount_minor bigint`, `currency char(3)`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: artisan, customer user, property nullable.  
Relationships: belongs to Artisan and customer; may have review, dispute, payment milestones.  
Indexes: artisan_id, customer_id, property_id, status, scheduled_at.  
Unique Constraints: none.  
Status Values: requested, quoted, accepted, scheduled, in_progress, completed, cancelled, disputed.  
Soft Delete: yes.

### 3.14 VerificationRequest

Purpose: Tracks verification of user, professional, property, ownership, or document set.  
Primary Key: `id uuid`.  
Fields: `type varchar(64)`, `target_entity_type varchar(80)`, `target_entity_id uuid`, `requester_id uuid`, `assignee_id uuid`, `status varchar(32)`, `decision varchar(32)`, `decision_reason text`, `expires_at timestamptz`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: requester user, assignee user.  
Relationships: polymorphic target; has documents through Document entity association.  
Indexes: type, target entity, requester_id, assignee_id, status, expires_at.  
Unique Constraints: optional one active request per target/type.  
Status Values: draft, submitted, needs_information, under_review, assigned, in_progress, verified, rejected, expired, revoked.  
Soft Delete: yes.

### 3.15 LegalReview

Purpose: Lawyer-led due diligence and legal opinion workflow.  
Primary Key: `id uuid`.  
Fields: `property_id uuid`, `requester_id uuid`, `lawyer_id uuid`, `status varchar(32)`, `risk_level varchar(32)`, `questions text`, `opinion_summary text`, `issued_at timestamptz`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: property, requester user, lawyer user nullable.  
Relationships: belongs to Property; has documents, messages, payment milestones.  
Indexes: property_id, requester_id, lawyer_id, status, risk_level, created_at.  
Unique Constraints: none.  
Status Values: draft, submitted, awaiting_documents, assigned, in_review, opinion_issued, closed, cancelled.  
Soft Delete: yes.

### 3.16 InspectionRequest

Purpose: Inspection or site visit request.  
Primary Key: `id uuid`.  
Fields: `type varchar(64)`, `property_id uuid`, `project_id uuid`, `requester_id uuid`, `inspector_id uuid`, `status varchar(32)`, `scope text`, `preferred_slots_json jsonb`, `scheduled_at timestamptz`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: property nullable, project nullable, requester user, inspector user nullable.  
Relationships: has inspection reports; may link to construction milestone through entity association if needed.  
Indexes: type, property_id, project_id, requester_id, inspector_id, status, scheduled_at.  
Unique Constraints: none.  
Status Values: requested, assigned, scheduled, in_progress, report_submitted, qa_review, released, cancelled.  
Soft Delete: yes.

### 3.17 InspectionReport

Purpose: Inspector findings and evidence summary.  
Primary Key: `id uuid`.  
Fields: `inspection_request_id uuid`, `inspector_id uuid`, `status varchar(32)`, `recommendation varchar(64)`, `summary text`, `checklist_json jsonb`, `submitted_at timestamptz`, `approved_by_id uuid`, `approved_at timestamptz`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: inspection request, inspector user, approved_by user.  
Relationships: belongs to InspectionRequest; has documents through Document association.  
Indexes: inspection_request_id, inspector_id, status, recommendation, submitted_at.  
Unique Constraints: none; report versions can be added later.  
Status Values: draft, submitted, revision_requested, approved, released, voided.  
Soft Delete: yes.

### 3.18 ConstructionProject

Purpose: Tracks a build/renovation project.  
Primary Key: `id uuid`.  
Fields: `owner_id uuid`, `property_id uuid`, `name varchar(180)`, `status varchar(32)`, `project_type varchar(64)`, `budget_amount_minor bigint`, `currency char(3)`, `start_date date`, `target_end_date date`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: owner user, property nullable.  
Relationships: has project milestones, inspection requests, payment milestones.  
Indexes: owner_id, property_id, status, target_end_date.  
Unique Constraints: none.  
Status Values: draft, active, on_hold, completed, cancelled, disputed.  
Soft Delete: yes.

### 3.19 ProjectMilestone

Purpose: Construction progress stage.  
Primary Key: `id uuid`.  
Fields: `project_id uuid`, `name varchar(120)`, `scope text`, `status varchar(32)`, `progress_percent smallint`, `start_date date`, `due_date date`, `approved_by_id uuid`, `approved_at timestamptz`, `sort_order int`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: project, approved_by user.  
Relationships: belongs to ConstructionProject; has payment milestones.  
Indexes: project_id, status, due_date, sort_order.  
Unique Constraints: `(project_id, name)` where deleted_at is null.  
Status Values: not_started, in_progress, submitted_for_inspection, inspection_scheduled, approved, rejected, rework_required, completed.  
Soft Delete: yes.

### 3.20 PaymentMilestone

Purpose: Tracks expected and externally confirmed payments.  
Primary Key: `id uuid`.  
Fields: `related_entity_type varchar(80)`, `related_entity_id uuid`, `payer_id uuid`, `payee_id uuid`, `amount_minor bigint`, `currency char(3)`, `status varchar(32)`, `due_date date`, `provider varchar(40)`, `external_reference varchar(160)`, `approved_by_id uuid`, `approved_at timestamptz`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: payer user, payee user, approved_by user.  
Relationships: polymorphic related entity; has payment events and disputes.  
Indexes: related entity, payer_id, payee_id, status, due_date, external_reference.  
Unique Constraints: external_reference per provider where not null.  
Status Values: pending, invoiced, paid_externally, proof_uploaded, under_review, approved, rejected, refunded_externally, cancelled, disputed.  
Soft Delete: yes.

### 3.21 Document

Purpose: Metadata and access policy for uploaded files.  
Primary Key: `id uuid`.  
Fields: `uploader_id uuid`, `entity_type varchar(80)`, `entity_id uuid`, `storage_provider varchar(40)`, `storage_key text`, `original_filename varchar(255)`, `content_type varchar(120)`, `size_bytes bigint`, `checksum varchar(128)`, `visibility varchar(32)`, `status varchar(32)`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: uploader user.  
Relationships: polymorphic entity; referenced by property media/documents and workflow entities.  
Indexes: uploader_id, entity_type/entity_id, status, visibility, checksum.  
Unique Constraints: storage_key per provider.  
Status Values: upload_pending, uploaded, processing, available, rejected, deleted.  
Soft Delete: yes.

### 3.22 Dispute

Purpose: Operational case for conflict, fraud, quality, or payment issues.  
Primary Key: `id uuid`.  
Fields: `complainant_id uuid`, `respondent_id uuid`, `related_entity_type varchar(80)`, `related_entity_id uuid`, `status varchar(32)`, `priority varchar(32)`, `category varchar(64)`, `description text`, `resolution text`, `assigned_admin_id uuid`, `resolved_at timestamptz`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: complainant user, respondent user nullable, assigned_admin user.  
Relationships: polymorphic related entity; has documents and messages.  
Indexes: complainant_id, respondent_id, related entity, status, priority, assigned_admin_id.  
Unique Constraints: none.  
Status Values: open, triaged, under_review, awaiting_response, resolved, rejected, escalated, closed.  
Soft Delete: yes.

### 3.23 Notification

Purpose: In-app and delivery-channel notification record.  
Primary Key: `id uuid`.  
Fields: `user_id uuid`, `type varchar(80)`, `title varchar(160)`, `body text`, `channel varchar(32)`, `status varchar(32)`, `read_at timestamptz`, `sent_at timestamptz`, `provider_message_id varchar(160)`, `metadata_json jsonb`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: user.  
Relationships: belongs to User.  
Indexes: user_id, status, read_at, created_at, type.  
Unique Constraints: optional idempotency key if added.  
Status Values: queued, sent, delivered, failed, read, archived.  
Soft Delete: yes.

### 3.24 AuditLog

Purpose: Immutable trail of sensitive actions and workflow transitions.  
Primary Key: `id uuid`.  
Fields: `actor_id uuid`, `action varchar(120)`, `entity_type varchar(80)`, `entity_id uuid`, `before_json jsonb`, `after_json jsonb`, `ip_address inet`, `user_agent text`, `request_id varchar(120)`, `created_at timestamptz`.  
Foreign Keys: actor user nullable for system.  
Relationships: belongs to actor.  
Indexes: actor_id, action, entity_type/entity_id, created_at, request_id.  
Unique Constraints: none.  
Status Values: none.  
Soft Delete: no.

### 3.25 Review

Purpose: User rating/review for completed service or marketplace interaction.  
Primary Key: `id uuid`.  
Fields: `author_id uuid`, `target_entity_type varchar(80)`, `target_entity_id uuid`, `booking_id uuid`, `rating smallint`, `comment text`, `status varchar(32)`, `moderated_by_id uuid`, `moderated_at timestamptz`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: author user, booking nullable, moderated_by user.  
Relationships: polymorphic target, often Artisan; may link ServiceBooking.  
Indexes: author_id, target entity, booking_id, status, rating.  
Unique Constraints: one review per author/booking where booking_id is not null.  
Status Values: published, hidden, flagged, removed.  
Soft Delete: yes.

### 3.26 MessageThread

Purpose: Scoped conversation attached to a listing, booking, review, inspection, dispute, or admin case.  
Primary Key: `id uuid`.  
Fields: `subject varchar(180)`, `context_entity_type varchar(80)`, `context_entity_id uuid`, `status varchar(32)`, `created_by_id uuid`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: created_by user.  
Relationships: has messages.  
Indexes: context entity, status, created_by_id, updated_at.  
Unique Constraints: none.  
Status Values: open, closed, archived.  
Soft Delete: yes.

### 3.27 Message

Purpose: Individual message in a thread.  
Primary Key: `id uuid`.  
Fields: `thread_id uuid`, `sender_id uuid`, `body text`, `message_type varchar(32)`, `metadata_json jsonb`, `created_at`, `updated_at`, `deleted_at`.  
Foreign Keys: thread, sender user.  
Relationships: belongs to MessageThread.  
Indexes: thread_id, sender_id, created_at.  
Unique Constraints: none.  
Status Values: text, system, attachment.  
Soft Delete: yes.

### 3.28 PaymentEvent

Purpose: Append-only normalized payment or escrow event ledger.  
Primary Key: `id uuid`.  
Fields: `payment_milestone_id uuid`, `provider varchar(40)`, `event_type varchar(80)`, `external_reference varchar(160)`, `amount_minor bigint`, `currency char(3)`, `status varchar(32)`, `payload_json jsonb`, `created_at timestamptz`.  
Foreign Keys: payment milestone.  
Relationships: belongs to PaymentMilestone; may map from WebhookEvent.  
Indexes: payment_milestone_id, provider, event_type, external_reference, created_at.  
Unique Constraints: `(provider, external_reference, event_type)` where external_reference is not null.  
Status Values: received, processed, ignored, failed.  
Soft Delete: no.

### 3.29 WebhookEvent

Purpose: Raw provider webhook storage and processing state.  
Primary Key: `id uuid`.  
Fields: `provider varchar(40)`, `event_id varchar(160)`, `event_type varchar(120)`, `signature_valid boolean`, `payload_json jsonb`, `processing_status varchar(32)`, `processed_at timestamptz`, `error_message text`, `created_at timestamptz`.  
Foreign Keys: none.  
Relationships: may produce PaymentEvent or other future event records.  
Indexes: provider, event_id, event_type, processing_status, created_at.  
Unique Constraints: `(provider, event_id)`.  
Status Values: received, processing, processed, failed, ignored.  
Soft Delete: no.

## 4. Cross-Entity Index Requirements

1. Public search: `Property(status, category, state, lga, price_minor, verification_status)`.
2. Geo search: GIST index on `Property.location_point`.
3. Queue operations: status + assignee/admin + created_at on verification, legal, inspection, dispute.
4. User dashboards: requester/customer/owner + status + updated_at on applications, viewings, bookings, reviews.
5. Payment operations: payment milestone status + due date; payment event provider references.
6. Messaging: thread updated_at and message thread_id/created_at.

