# RealityNG Version 2.0 Feature Inventory

## Backend Stack

- Python 3.12
- Django 5.1
- Django REST Framework
- Simple JWT with token blacklist
- drf-spectacular OpenAPI
- django-filter
- django-cors-headers
- PostgreSQL
- Redis
- MinIO/S3-compatible media storage
- Gunicorn
- Docker Compose

## Frontend Stack

- Next.js 15
- React 19
- TypeScript
- TanStack React Query
- Axios
- React Hook Form
- Zod
- Tailwind CSS
- Vitest
- Vercel deployment

## Core Feature Inventory

### Authentication

- Registration
- Login
- Refresh token
- Logout/token invalidation
- Password reset flow
- Current user profile endpoint
- Role request flow
- Admin role approval/rejection

### Authorization

- Role-aware dashboards
- Admin-only moderation endpoints
- Object-level ownership checks
- Suspended-user handling
- Suspended-provider handling
- Public/private serializer separation

### Property Marketplace

- Property CRUD
- Public property browsing
- Property search/filtering
- Property detail pages
- Property media
- Favorites
- Inquiries/show interest
- Viewing requests
- Rental applications
- Dashboard activity
- Transaction center

### Verification

- User verification requests
- Property verification
- Private verification documents
- Signed URL access
- Admin verification review
- Approval, rejection, and request-more-information states
- Public verification-safe display

### Google Maps Architecture

- Location fields and precision rules
- Approximate/public-safe location support
- Map/list/split-view frontend foundation
- Maps fallback when production key is unavailable
- Production activation deferred pending Google Cloud billing and restricted API key

### AI Assistant

- Assistant provider architecture
- Demo provider mode
- Anthropic provider preserved but inactive unless configured
- Conversation persistence
- Demo assistant supported topics
- Backend-driven assistant config
- Frontend does not decide provider mode independently

### Provider Marketplace

- Trade categories
- Public category API
- Public provider API
- Public provider detail page
- Provider search and filtering
- Active-only public visibility

### Provider Profiles

- One provider profile per user
- Profile lifecycle
- Provider type, business identity, biography, contact preferences
- Public-safe location display
- Verification snapshot display
- Admin approval/rejection/request-more-information

### Portfolio

- Provider portfolio image model
- Upload validation
- Public media storage
- Cover image support
- Reordering support
- Owner-only management

### Service Areas

- Country, state, city, LGA, neighborhood
- Optional radius
- One primary service area
- Public-safe display
- Works without Google Maps

### Quote Requests

- Public quote request submission
- Anonymous contact validation
- Authenticated customer support
- Provider quote request dashboard
- Status transitions: submitted, viewed, responded, closed, cancelled
- Admin quote queue

### Booking Foundation

- Minimal service booking model
- Completed booking lifecycle
- Review eligibility linkage
- Not a full scheduling or payment system

### Reviews and Trust Signals

- Booking-linked reviews
- One review per completed booking
- Rating dimensions
- Provider rating aggregates
- Provider response
- Review flagging foundation
- Admin moderation
- Public review listing
- Trust signals derived from verification and published review data

### Dashboards

- Customer services dashboard
- Provider services dashboard
- Admin services dashboard
- Buyer/property dashboard
- Dashboard summaries, recent activity, and operational queues

### Complaints and Appeals

- Customer/provider complaints
- Complaint evidence foundation
- Complaint moderation
- Provider warnings
- Provider suspension/reactivation
- Provider appeals
- Admin appeals queue
- Audit events for sensitive transitions

### Governance and Admin Moderation

- Provider profile moderation
- Quote request moderation
- Review moderation
- Complaint moderation
- Warning/suspension workflows
- Appeal decision workflows
- Admin-only access controls

### Release Hardening

- Services permission matrix
- Upload validation hardening
- Suspended-provider mutation restrictions
- Release readiness checklist
- Rollback guide
- Staging load-test plan
- Production deployment report

## Backend API Inventory

Top-level mounted groups:

- `/api/v1/auth/`
- `/api/v1/users/`
- `/api/v1/roles/`
- `/api/v1/properties/`
- `/api/v1/public/properties/`
- `/api/v1/favorites/`
- `/api/v1/inquiries/`
- `/api/v1/viewings/`
- `/api/v1/applications/`
- `/api/v1/dashboard/`
- `/api/v1/verifications/`
- `/api/v1/property-verifications/`
- `/api/v1/assistant/`
- `/api/v1/conversations/`
- `/api/v1/services/`
- `/api/v1/health/`
- `/api/schema/`
- `/api/docs/`

Key services endpoints:

- `/api/v1/services/categories/`
- `/api/v1/services/providers/`
- `/api/v1/services/providers/{slug}/`
- `/api/v1/services/providers/{slug}/quote-requests/`
- `/api/v1/services/providers/{slug}/reviews/`
- `/api/v1/services/provider-profile/`
- `/api/v1/services/provider-profile/me/`
- `/api/v1/services/provider-profile/submit/`
- `/api/v1/services/provider-profile/trades/`
- `/api/v1/services/provider-profile/service-areas/`
- `/api/v1/services/provider-profile/portfolio/`
- `/api/v1/services/provider-profile/quote-requests/`
- `/api/v1/services/provider-profile/reviews/`
- `/api/v1/services/provider-profile/complaints/`
- `/api/v1/services/provider-profile/appeals/`
- `/api/v1/services/reviews/`
- `/api/v1/services/complaints/`
- `/api/v1/services/dashboard/customer/`
- `/api/v1/services/dashboard/provider/`
- `/api/v1/services/dashboard/admin/`
- `/api/v1/services/admin/providers/`
- `/api/v1/services/admin/quote-requests/`
- `/api/v1/services/admin/reviews/`
- `/api/v1/services/admin/complaints/`
- `/api/v1/services/admin/appeals/`

## Frontend Route Inventory

Public routes:

- `/`
- `/about`
- `/contact`
- `/help`
- `/properties`
- `/properties/[slug]`
- `/services`
- `/services/providers/[slug]`
- `/safety`
- `/listing-standards`
- `/verification-standards`
- `/privacy`
- `/terms`
- `/refunds`
- `/data-deletion`

Authentication routes:

- `/auth/sign-in`
- `/auth/sign-up`
- `/auth/forgot-password`
- `/auth/reset-password`
- `/onboarding/role-setup`

Customer/dashboard routes:

- `/dashboard`
- `/dashboard/services`
- `/dashboard/services/reviews`
- `/dashboard/services/bookings/[bookingId]/review`
- `/dashboard/services/complaints`
- `/dashboard/services/complaints/[id]`
- `/saved-properties`
- `/settings/profile`
- `/apply/[propertyId]`

Provider/artisan routes:

- `/dashboard/artisan`
- `/dashboard/artisan/profile`
- `/dashboard/artisan/portfolio`
- `/dashboard/artisan/quote-requests`
- `/dashboard/artisan/reviews`
- `/dashboard/artisan/complaints`
- `/dashboard/artisan/complaints/[id]`
- `/dashboard/artisan/appeals`
- `/dashboard/artisan/appeals/[id]`

Property owner/listing routes:

- `/properties/new`
- `/verification`
- `/verification/new`
- `/verification/property/[propertyId]/new`

Admin routes:

- `/admin`
- `/admin/verifications`
- `/admin/services`
- `/admin/services/providers`
- `/admin/services/providers/[id]`
- `/admin/services/quote-requests`
- `/admin/services/reviews`
- `/admin/services/reviews/[id]`
- `/admin/services/complaints`
- `/admin/services/complaints/[id]`
- `/admin/services/appeals`
- `/admin/services/appeals/[id]`

## Database Migration Inventory

Current project migration count:

```text
27 app migrations
```

Services marketplace migrations:

- `apps/services/migrations/0001_initial.py`
- `apps/services/migrations/0002_seed_trade_categories.py`
- `apps/services/migrations/0003_portfolioimage_servicearea_is_primary_and_more.py`
- `apps/services/migrations/0004_quoterequest.py`
- `apps/services/migrations/0005_servicebooking.py`
- `apps/services/migrations/0006_serviceprovider_average_communication_rating_and_more.py`
- `apps/services/migrations/0007_providerappeal_servicecomplaint_and_more.py`

Location-intelligence migration:

- `apps/properties/migrations/0008_property_display_location_property_geocoding_status_and_more.py`

Assistant migrations:

- `apps/assistant/migrations/0001_initial.py`
- `apps/assistant/migrations/0002_aiconversation_total_input_tokens_and_more.py`
- `apps/assistant/migrations/0003_alter_aiconversation_provider.py`

Trust migrations:

- `apps/trust/migrations/0001_initial.py`
- `apps/trust/migrations/0002_alter_verificationdocument_file.py`
- `apps/trust/migrations/0003_alter_verificationdocument_file.py`
- `apps/trust/migrations/0004_verificationdocument_property_verification_and_more.py`
- `apps/trust/migrations/0005_verificationdocument_document_has_exactly_one_parent.py`

