# RealityNG Fullstack Engineer Handoff

Prepared for: Incoming Fullstack Engineer  
Prepared by: RealityNG delivery handoff  
Date: 2026-07-14  
Project: RealityNG, diaspora-focused Nigerian PropTech platform  

---

## 1. Executive Summary

RealityNG is a Nigerian PropTech marketplace for diaspora and local users to discover, verify, buy, rent, list, manage, and transact around properties in Nigeria.

The project currently has two active repositories:

1. Backend: `https://github.com/akordonald15-hue/realityng-backend`
2. Frontend: `https://github.com/akordonald15-hue/realityng-frontend`

The production frontend is hosted on Vercel. The backend is deployed on a VPS at `204.168.221.252` and is exposed through Cloudflare HTTPS at:

```text
https://api.realityng.com/api/v1
```

Current backend health endpoint:

```text
https://api.realityng.com/api/v1/health/
```

Expected payload:

```json
{
  "status": "ok",
  "service": "realityng-backend",
  "version": "0.1.0"
}
```

The platform has completed the marketplace foundation, authentication, roles, listings, media, favorites, inquiry workflow, viewing workflow, rental application workflow, dashboards, demo mode, frontend branding alignment, onboarding conversion refinements, and backend VPS deployment.

The next planned product sprint is Sprint 6: Verification Layer.

---

## 2. Current Repository State

### Backend Repository

Repository:

```text
https://github.com/akordonald15-hue/realityng-backend
```

Branch:

```text
main
```

Current deployed commit:

```text
1c9524b11a0985ba462b8c500f24c16f803bb01e
```

Latest backend commits at handoff:

```text
1c9524b Allow HTTP-compatible secure cookie settings
85325f6 Exclude health checks from API throttling
aaff108 Support shared proxy VPS deployment
9533da5 Add lean VPS production compose
0a345ad Harden API security controls
00b2b20 Add workflow transaction dashboard endpoints
933c374 Add rental application workflow
78bd47b Add viewing request workflow
```

Local backend path used during development:

```text
C:\Users\akord\OneDrive\Desktop\Realityng\backend
```

### Frontend Repository

Repository:

```text
https://github.com/akordonald15-hue/realityng-frontend
```

Branch:

```text
main
```

Current pushed commit:

```text
7f324b5f8919298d709ab1d2ae5052aba0ea964d
```

Latest frontend commits at handoff:

```text
7f324b5 Refine branding and onboarding conversion flow
bf14cf5 Align frontend with CEO navigation feedback
c4c134d Harden demo mode security boundary
065211b Add workflow transaction dashboards
1c4ad9f Add rental application frontend flow
```

Local frontend path used during development:

```text
C:\Users\akord\OneDrive\Desktop\Realityng\frontend
```

---

## 3. Production and Deployment State

### Frontend Deployment

The frontend is deployed on Vercel.

Production frontend environment variables should be:

```env
NEXT_PUBLIC_USE_MOCKS=false
NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1
```

For demo-only mode, use:

```env
NEXT_PUBLIC_USE_MOCKS=true
```

Do not use demo mode for production backend integration.

### Backend Deployment

Backend VPS:

```text
204.168.221.252
```

Backend deployment path:

```text
/opt/realityng/backend
```

Backend deployment project name:

```text
realityng
```

Running RealityNG services:

```text
realityng-backend-1
realityng-postgres-1
realityng-redis-1
```

RealityNG backend is exposed locally on the VPS through:

```text
127.0.0.1:18000 -> backend:8000
```

Public traffic flow:

```text
Browser
-> Cloudflare HTTPS
-> VPS HTTP origin on port 80
-> existing Telehealth Nginx container
-> realityng-backend:8000
```

Important: the server also hosts a separate Telehealth production stack. Do not restart, remove, prune, or modify Telehealth application services.

### Shared Proxy Network

Docker network:

```text
shared-proxy
```

Members:

```text
telehealthapp-nginx-1
realityng-backend-1
```

RealityNG Postgres and Redis are not attached to `shared-proxy` and must remain private.

### Cloudflare HTTPS Status

Cloudflare currently terminates public HTTPS for:

```text
api.realityng.com
```

Current mode:

```text
Flexible SSL
```

This is transitional. Browser-to-Cloudflare traffic is HTTPS, but Cloudflare-to-origin traffic is HTTP.

Do not present Flexible SSL as final production security. The future target should be:

```text
Cloudflare Full (strict)
+ Cloudflare Origin Certificate or valid public origin certificate
+ origin HTTPS on port 443
+ HSTS only after Full (strict) is stable
```

### Latest Backend Deployment Result

Latest deployment used release archive from backend commit:

```text
1c9524b11a0985ba462b8c500f24c16f803bb01e
```

Backup created on VPS:

```text
/opt/realityng/backend.backup-20260714-081013
```

Previous replaced folder:

```text
/opt/realityng/backend.replaced-20260714-081013
```

Validation after deployment:

```text
Migrations: no migrations to apply
Collectstatic: 154 static files copied
Django check: no issues
RealityNG HTTPS health: OK
Telehealth health: OK
```

Expected transitional Django deploy warnings:

```text
SECURE_HSTS_SECONDS not set
SECURE_SSL_REDIRECT not true
```

These are deferred while Cloudflare Flexible SSL remains in use.

---

## 4. Product and Sprint Status

### Completed Work

The following work is complete or functionally implemented:

1. Sprint 0: infrastructure and architecture foundation.
2. Sprint 1: authentication, roles, profiles, role approval, audit log foundation.
3. Sprint 2: property listings core and public browsing.
4. Sprint 3: property image and gallery management.
5. Sprint 3.5: branding and design system alignment.
6. Sprint 3.6: frontend integration, navigation, accessibility audit.
7. Sprint 4: favorites, saved properties, and dashboard foundations.
8. Demo mode: mock auth, mock properties, mock dashboards, mock inquiries, mock workflow data.
9. CEO alignment and branding revisions:
   - Bigger logo treatment.
   - Correct slogan: `Where Dreams Find An Address`.
   - Logo use across navbar, splash/loading, footer, favicon/app assets.
   - Solutions for artisans shown on landing page.
   - Show Interest button added and later connected to backend inquiry workflow.
10. Sprint 5 Phase 1: Show Interest and inquiry workflow.
11. Sprint 5 Phase 2: viewing request and scheduling workflow.
12. Sprint 5 Phase 3: rental application workflow.
13. Sprint 5 Phase 4: workflow integration and operational dashboards.
14. Sprint 5.5 security/deployment hardening:
   - Object-level permission checks.
   - File upload validation.
   - Demo mode boundary hardening.
   - HTTP-compatible secure-cookie configuration for Cloudflare Flexible transition.
15. Backend VPS deployment and Cloudflare HTTPS validation.
16. Frontend API integration readiness with Vercel environment variables.
17. Latest frontend conversion refinement:
   - Navbar slogan under logo/wordmark.
   - Hero duplicate branding removed.
   - Footer simplified.
   - Reusable role-selection modal.
   - Protected action gating.
   - Post-auth return handling.

### Current Product Stage

RealityNG is now past the MVP marketplace transaction foundation.

The platform supports:

1. Visitor property discovery.
2. Mock/demo experience for stakeholders.
3. Real backend authentication.
4. Role-based user journeys.
5. Property creation and moderation.
6. Property media gallery.
7. Favorites and saved properties.
8. Inquiries.
9. Viewing requests.
10. Rental applications.
11. Buyer, landlord/agent, and admin dashboard foundations.
12. Activity feed and transaction-center style workflow summaries.

The next major sprint is:

```text
Sprint 6: Verification Layer
```

---

## 5. Technology Stack

### Frontend Stack

Framework and language:

```text
Next.js App Router
React 19
TypeScript
```

Styling and UI:

```text
Tailwind CSS
Custom shared design system
Playfair Display for headings
Inter for body text
RealityNG brand palette
```

State and data:

```text
TanStack Query
Axios
React Context providers
LocalStorage for mock/demo session and token storage
```

Forms and validation:

```text
React Hook Form
Zod
```

Testing and quality:

```text
Vitest
React Testing Library
ESLint
Prettier
TypeScript typecheck
```

Key frontend scripts:

```bash
npm run dev
npm run lint
npm run typecheck
npm run test
npm run build
```

Important note: on the Windows/OneDrive development machine, `next build` compiled successfully and generated all static pages, but repeatedly hung at Next.js `Collecting build traces`. This appears environment-specific. Vercel should perform the canonical production build.

### Backend Stack

Framework and language:

```text
Python 3.12
Django 5.1
Django REST Framework
```

Authentication:

```text
Custom UUID user model
JWT via djangorestframework-simplejwt
Refresh token blacklist
Role-based permissions
Object-level permissions
```

Database and cache:

```text
PostgreSQL 16
Redis 7
```

Background jobs:

```text
Celery
Django Celery Beat
Redis broker/result backend
```

API tooling:

```text
DRF Spectacular OpenAPI schema
Django Filter
Pagination, filtering, searching, ordering
```

Storage:

```text
MinIO for local development
S3-compatible storage abstraction through boto3/django-storages
Filesystem media fallback for tests/local paths
```

Runtime and deployment:

```text
Docker
Docker Compose
Gunicorn
Whitenoise
Cloudflare edge HTTPS
Shared Nginx reverse proxy through existing Telehealth Nginx
```

Monitoring and logging:

```text
Structured JSON logging
Request correlation IDs
Sentry placeholders
AuditLog model
```

Testing and quality:

```text
pytest
pytest-django
ruff
Django system checks
OpenAPI generation/validation
```

Backend validation commands:

```bash
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py spectacular --validate
pytest
```

---

## 6. Backend Architecture

### Backend Apps

Current Django apps:

```text
apps.accounts
apps.common
apps.core
apps.properties
```

Responsibilities:

1. `apps.accounts`
   - Custom user model.
   - User profile.
   - Roles.
   - UserRole approval flow.
   - Auth endpoints.
   - Admin role approval endpoints.
   - Account audit logs.

2. `apps.common`
   - Shared model primitives.
   - UUID primary key mixins.
   - Timestamp mixins.
   - Soft-delete mixins.

3. `apps.core`
   - Health endpoint.
   - Middleware/helpers for request IDs and logging.

4. `apps.properties`
   - Property listings.
   - Public property browsing.
   - Property media.
   - Favorites.
   - Inquiries.
   - Viewings.
   - Rental applications.
   - Dashboard summaries.
   - Transaction center.
   - Activity feed.

### Core Backend Models

Accounts:

```text
User
UserProfile
Role
UserRole
AuditLog
```

Properties and transaction workflow:

```text
Property
PropertyImage
Favorite
Inquiry
Viewing
RentalApplication
```

### Main Workflow Relationships

The intended transaction workflow is:

```text
Property
-> Inquiry
-> Viewing
-> RentalApplication
-> Owner/Admin decision
```

Important relationship design:

1. Inquiry and Viewing are linked but separate.
2. A Viewing belongs to an Inquiry.
3. A RentalApplication may link to an Inquiry and a Viewing.
4. This leaves room for future workflows where:
   - A user can apply without a viewing.
   - One inquiry can have multiple viewing requests.
   - A viewing can be rescheduled without rewriting inquiry history.

### Status Pipelines

Inquiry:

```text
new
-> contacted
-> viewing_scheduled
-> negotiating
-> converted
or closed
```

Viewing:

```text
requested
-> confirmed
-> completed

requested
-> rescheduled
-> confirmed
-> completed

requested/confirmed/rescheduled
-> cancelled
```

Rental Application:

```text
submitted
-> under_review
-> approved
or rejected
or withdrawn
```

Property:

```text
draft
-> pending_review
-> approved
or rejected
or archived
```

### Important Backend Endpoints

Base API URL:

```text
/api/v1
```

Health:

```text
GET /api/v1/health/
```

Authentication:

```text
POST /api/v1/auth/register/
POST /api/v1/auth/login/
POST /api/v1/auth/logout/
POST /api/v1/auth/token/refresh/
POST /api/v1/auth/forgot-password/
POST /api/v1/auth/reset-password/
GET  /api/v1/users/me/
PATCH /api/v1/users/me/
```

Roles:

```text
GET  /api/v1/roles/
POST /api/v1/roles/request/
GET  /api/v1/admin/role-requests/
POST /api/v1/admin/role-requests/{id}/approve/
POST /api/v1/admin/role-requests/{id}/reject/
```

Properties:

```text
GET    /api/v1/properties/
POST   /api/v1/properties/
GET    /api/v1/properties/{slug}/
PATCH  /api/v1/properties/{slug}/
DELETE /api/v1/properties/{slug}/
POST   /api/v1/properties/{slug}/submit-for-review/
POST   /api/v1/properties/{slug}/approve/
POST   /api/v1/properties/{slug}/reject/
```

Public properties:

```text
GET /api/v1/public/properties/
GET /api/v1/public/properties/{slug}/
```

Property images:

```text
GET    /api/v1/properties/{slug}/images/
POST   /api/v1/properties/{slug}/images/
PATCH  /api/v1/properties/{slug}/images/{image_id}/
DELETE /api/v1/properties/{slug}/images/{image_id}/
POST   /api/v1/properties/{slug}/images/{image_id}/set-cover/
```

Favorites:

```text
GET    /api/v1/favorites/
POST   /api/v1/favorites/
DELETE /api/v1/favorites/{property_id}/
```

Inquiries:

```text
GET    /api/v1/inquiries/
POST   /api/v1/inquiries/
GET    /api/v1/inquiries/{id}/
GET    /api/v1/inquiries/received/
POST   /api/v1/inquiries/{id}/status/
PATCH  /api/v1/inquiries/{id}/notes/
```

Viewings:

```text
GET   /api/v1/viewings/
POST  /api/v1/viewings/
GET   /api/v1/viewings/{id}/
GET   /api/v1/viewings/received/
POST  /api/v1/viewings/{id}/confirm/
POST  /api/v1/viewings/{id}/reschedule/
POST  /api/v1/viewings/{id}/cancel/
POST  /api/v1/viewings/{id}/complete/
PATCH /api/v1/viewings/{id}/notes/
```

Applications:

```text
GET   /api/v1/applications/
POST  /api/v1/applications/
GET   /api/v1/applications/{id}/
GET   /api/v1/applications/received/
POST  /api/v1/applications/{id}/under-review/
POST  /api/v1/applications/{id}/approve/
POST  /api/v1/applications/{id}/reject/
POST  /api/v1/applications/{id}/withdraw/
PATCH /api/v1/applications/{id}/notes/
```

Dashboards:

```text
GET /api/v1/dashboard/summary/
GET /api/v1/dashboard/activity/
GET /api/v1/dashboard/transactions/
```

OpenAPI:

```text
GET /api/schema/
GET /api/docs/
```

---

## 7. Frontend Architecture

### App Routes

Important route groups and pages:

```text
src/app/page.tsx
src/app/(public)/properties/page.tsx
src/app/(public)/properties/[slug]/page.tsx
src/app/auth/sign-in/page.tsx
src/app/auth/sign-up/page.tsx
src/app/onboarding/role-setup/page.tsx
src/app/(dashboard)/dashboard/page.tsx
src/app/(dashboard)/properties/new/page.tsx
src/app/apply/[propertyId]/page.tsx
src/app/saved-properties/page.tsx
src/app/settings/profile/page.tsx
src/app/(admin)/admin/page.tsx
```

### Important Component Areas

```text
src/components/brand
src/components/layout
src/components/ui
src/components/forms
src/components/auth
src/components/properties
src/components/workflow
```

### Important Providers

```text
src/providers/auth-provider.tsx
src/providers/app-providers.tsx
src/providers/compare-provider.tsx
```

`app-providers.tsx` wraps the application with:

1. TanStack Query.
2. Auth provider.
3. Role-selection modal provider.
4. Compare provider.
5. Sign-up prompt.

### API Layer

Frontend API modules live under:

```text
src/lib/api
```

Important files:

```text
src/lib/api/client.ts
src/lib/api/auth.ts
src/lib/api/properties.ts
src/lib/api/inquiries.ts
src/lib/api/viewings.ts
src/lib/api/applications.ts
src/lib/api/dashboard.ts
```

The API client uses:

```text
NEXT_PUBLIC_API_BASE_URL
```

For production:

```env
NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1
```

### Demo Mode

Demo mode is controlled by:

```env
NEXT_PUBLIC_USE_MOCKS=true
```

Mock data files:

```text
src/mocks/mock-auth.ts
src/mocks/mock-users.ts
src/mocks/mock-properties.ts
src/mocks/mock-inquiries.ts
src/mocks/mock-viewings.ts
src/mocks/mock-applications.ts
src/mocks/mock-dashboard.ts
src/mocks/mock-workflow.ts
```

Demo login accounts:

```text
admin@realityng.com / password123
agent@realityng.com / password123
buyer@realityng.com / password123
```

These are demo-only accounts. They must not be treated as production credentials.

### Latest Frontend Conversion Flow

Current intended user journey:

```text
Visitor
-> Browse homepage/properties/property detail
-> Click important action
-> Role-selection modal
-> Sign up with role prefilled
-> Sign in
-> Return to intended page/action
```

Protected actions currently include:

```text
Save Property
Compare Property
Show Interest
Request Viewing
Apply For Property
Contact Agent, when added
List Property
Artisan Booking, when added
Dashboard
Create Listing
```

Public users can still:

```text
Browse homepage
Browse listings
View property details
```

---

## 8. Branding and UX Notes

Official slogan:

```text
Where Dreams Find An Address
```

Important: use `An Address`, not `Address`.

Brand colors:

```text
Primary: #0F3D2E
Secondary/Gold: #D4A017
Background: #081C15
Surface: #11241D
Text: #FFFFFF
Muted text: #C8C8C8
```

Typography:

```text
Headings: Playfair Display
Body: Inter
```

Current branding rules:

1. Header/nav uses transparent logo with slogan underneath.
2. Hero should not repeat the company name.
3. Hero starts with `TRUSTED NIGERIAN PROPERTY DISCOVERY`.
4. Footer keeps logo and slogan but avoids clutter.
5. Do not place the logo in a white rounded rectangle.
6. Keep mobile layout clean; slogan should not wrap awkwardly.

Latest frontend screenshots were captured locally under:

```text
C:\Users\akord\OneDrive\Desktop\Realityng\screenshots
```

Key screenshot files:

```text
mobile-navbar.png
updated-hero.png
footer.png
account-role-modal.png
protected-action-flow.png
post-login-return-flow.png
```

---

## 9. Local Development Setup

### Backend Local Setup

Clone backend:

```bash
git clone https://github.com/akordonald15-hue/realityng-backend.git
cd realityng-backend
```

Create local environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements\local.txt
Copy-Item .env.example .env
```

Docker local development:

```bash
docker compose up --build
```

Run local migrations:

```bash
python manage.py migrate
```

Run local backend:

```bash
python manage.py runserver
```

Backend local URLs:

```text
http://localhost:8000/api/v1/health/
http://localhost:8000/api/docs/
http://localhost:8000/admin/
```

### Frontend Local Setup

Clone frontend:

```bash
git clone https://github.com/akordonald15-hue/realityng-frontend.git
cd realityng-frontend
```

Install dependencies:

```bash
npm install
```

Create local env file:

```env
NEXT_PUBLIC_USE_MOCKS=false
NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1
```

For offline demo development:

```env
NEXT_PUBLIC_USE_MOCKS=true
```

Run frontend:

```bash
npm run dev
```

Frontend local URL:

```text
http://localhost:3000
```

---

## 10. Git Branch and Pull Request Workflow

The engineer should not commit directly to `main`.

### Initial Setup

Clone the repo:

```bash
git clone https://github.com/akordonald15-hue/realityng-frontend.git
cd realityng-frontend
```

or:

```bash
git clone https://github.com/akordonald15-hue/realityng-backend.git
cd realityng-backend
```

Make sure local `main` is current:

```bash
git checkout main
git pull origin main
```

Create a feature branch:

```bash
git checkout -b feature/sprint-6-verification-layer
```

Recommended branch naming:

```text
feature/<short-feature-name>
fix/<short-bug-name>
chore/<maintenance-name>
security/<security-task-name>
docs/<documentation-name>
```

Examples:

```bash
git checkout -b feature/agent-verification
git checkout -b feature/property-verification-badges
git checkout -b fix/favorite-auth-gate
git checkout -b security/cors-hardening
```

### Daily Work Rules

Before coding:

```bash
git checkout main
git pull origin main
git checkout your-branch
git merge main
```

Check what changed before staging:

```bash
git status
git diff
```

Stage intentionally:

```bash
git add <files>
```

Commit with a clear message:

```bash
git commit -m "Add agent verification request workflow"
```

Push the branch:

```bash
git push -u origin feature/agent-verification
```

### Pull Request Process

Strictly speaking, a pull request cannot be opened on GitHub until the branch exists on GitHub. So the correct process is:

```text
Create local branch
-> Commit changes
-> Push branch
-> Open pull request from branch into main
```

Open the PR on GitHub:

```text
base: main
compare: feature/agent-verification
```

PR title format:

```text
Sprint 6: Add agent verification workflow
```

PR description should include:

```md
## Summary
- What changed
- Why it changed

## Scope
- Frontend changes
- Backend changes
- Database migrations
- API changes

## Validation
- [ ] Backend lint passed
- [ ] Backend tests passed
- [ ] Frontend lint passed
- [ ] Frontend typecheck passed
- [ ] Frontend tests passed
- [ ] Frontend build passed

## Screenshots
- Add before/after screenshots for UI changes

## Deployment Notes
- Any env vars
- Any migrations
- Any manual deployment steps

## Risks
- Security risks
- Rollback notes
- Known limitations
```

Do not merge a PR until:

1. The branch is up to date with `main`.
2. Tests pass.
3. Migrations are reviewed.
4. API changes are reflected in frontend types/services.
5. Screenshots are attached for UI changes.
6. The owner has reviewed and approved.

### Git Email

The Git email should match the GitHub account:

```bash
git config user.email "akordonald15@gmail.com"
```

This matters because Vercel deployment was previously blocked when the commit email did not match a GitHub account.

---

## 11. Validation Requirements

### Backend Validation Before PR

Run:

```bash
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
pytest
```

If API schema changes:

```bash
python manage.py spectacular --validate
```

If migrations are added:

```bash
python manage.py migrate --noinput
```

### Frontend Validation Before PR

Run:

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

If `npm run build` hangs locally on Windows/OneDrive at `Collecting build traces`, do not ignore compile errors. Confirm the log reached:

```text
Compiled successfully
Generating static pages (17/17)
```

Then also rely on Vercel build as the final production build check.

### Deployment Validation

Backend health:

```bash
curl -i https://api.realityng.com/api/v1/health/
```

Frontend production environment:

```env
NEXT_PUBLIC_USE_MOCKS=false
NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1
```

---

## 12. Backend Deployment Notes for Engineer

Current VPS source folder is not a Git checkout. It was deployed from a release archive while preserving `.env.production`.

Safe deployment pattern used:

1. Build/push backend repo locally.
2. Create a release archive from the backend repository `HEAD`.
3. Copy archive to `/opt/realityng`.
4. Extract into a new folder.
5. Copy existing `/opt/realityng/backend/.env.production`.
6. Validate compose config.
7. Back up existing backend folder.
8. Swap new folder into `/opt/realityng/backend`.
9. Rebuild/recreate only the RealityNG backend container.
10. Run migrations and collectstatic.
11. Validate health.

Example local archive command:

```bash
git archive --format=tar -o ../realityng-backend-release-<hash>.tar HEAD
```

Copy to server:

```bash
scp ../realityng-backend-release-<hash>.tar root@204.168.221.252:/opt/realityng/
```

Backend restart command:

```bash
cd /opt/realityng/backend

docker compose \
  -p realityng \
  -f docker-compose.yml \
  -f compose.production.yaml \
  up -d --no-deps --build backend
```

Post-deploy:

```bash
docker compose \
  -p realityng \
  -f docker-compose.yml \
  -f compose.production.yaml \
  exec backend python manage.py migrate --noinput

docker compose \
  -p realityng \
  -f docker-compose.yml \
  -f compose.production.yaml \
  exec backend python manage.py collectstatic --noinput

docker compose \
  -p realityng \
  -f docker-compose.yml \
  -f compose.production.yaml \
  exec backend python manage.py check
```

Do not run:

```bash
docker system prune
docker volume prune
docker compose down -v
```

Do not restart Telehealth unless explicitly approved.

### Rollback

If a backend deployment fails:

```bash
cd /opt/realityng
mv backend backend.failed-<timestamp>
cp -a backend.backup-<timestamp> backend
cd /opt/realityng/backend
docker compose -p realityng -f docker-compose.yml -f compose.production.yaml up -d --no-deps --build backend
```

Then verify:

```bash
curl -i https://api.realityng.com/api/v1/health/
curl -i https://api.caretekk.com/health/
```

---

## 13. Security and Production Notes

### Do Not Expose Secrets

Never commit:

```text
.env
.env.production
database passwords
JWT signing secrets
Sentry DSNs if private
Cloudflare credentials
VPS SSH keys
```

### CORS and CSRF

Production should allow only approved origins:

```text
https://realityng.com
https://www.realityng.com
https://api.realityng.com
http://localhost:3000
```

Do not use wildcard CORS.

### Secure Cookie / SSL Note

Current transitional settings are designed for Cloudflare Flexible SSL:

```env
SECURE_SSL_REDIRECT=false
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

Do not enable `SECURE_SSL_REDIRECT=true` until origin HTTPS is implemented and tested. Otherwise, Flexible SSL may create redirect loops.

### WebSocket Note

WebSocket support is not currently implemented as an application feature. Do not configure WSS or claim WebSocket support until the codebase includes ASGI Channels or an equivalent WebSocket implementation.

### File Uploads

Property media upload validation exists:

```text
Allowed MIME types
Allowed extensions
Max size
Max image count
Image verification
Owner/admin-only permissions
Single cover image rule
```

Current local object storage uses MinIO. Production object storage is still pending final setup.

---

## 14. What Is Remaining

### Immediate Engineering Follow-Up

1. Confirm the latest Vercel frontend deployment succeeded after commit `7f324b5`.
2. Confirm Vercel production env values:

```env
NEXT_PUBLIC_USE_MOCKS=false
NEXT_PUBLIC_API_BASE_URL=https://api.realityng.com/api/v1
```

3. Run a full browser smoke test:
   - Register.
   - Login.
   - Role onboarding.
   - Browse properties.
   - Save property.
   - Show Interest.
   - Request viewing.
   - Submit application.
   - Dashboard.
   - Logout.

4. Verify CORS from:

```text
https://realityng.com
https://www.realityng.com
```

5. Monitor backend logs for 24 hours after frontend traffic increases.

### Sprint 6: Verification Layer

Sprint 6 should implement:

1. CAC verification.
2. Agent verification.
3. Property verification.
4. Verification badges.
5. Verification status tracking.
6. Admin review screens for verification requests.
7. Frontend trust badge display.
8. Backend permissions and audit events.
9. Tests for verification workflows.

Recommended backend models:

```text
AgentVerification
PropertyVerification
BusinessVerification
VerificationDocument
VerificationDecision
```

Recommended statuses:

```text
draft
submitted
under_review
approved
rejected
expired
revoked
```

Recommended audit events:

```text
verification_submitted
verification_approved
verification_rejected
verification_revoked
```

### Future Roadmap After Sprint 6

Approved roadmap direction:

1. Sprint 7: AI Assistant Foundation.
2. Sprint 8: Google Maps and location intelligence.
3. Sprint 9: Artisan marketplace.
4. Sprint 10: Inspection workflow.
5. Sprint 11: Construction project tracking.
6. Sprint 12: Lead management and inquiries expansion.
7. Sprint 13: Notifications and messaging.
8. Sprint 14: Payments and transaction tracking.
9. Sprint 15: Admin operations and beta launch.

Features removed from roadmap:

```text
Lawyer marketplace
Lawyer workflow
Legal review workflow
Lawyer dashboards
Lawyer assignment flows
```

Features moved to future phase:

```text
Remote property monitoring
CCTV integration
Smart property management
IoT monitoring
```

---

## 15. Known Risks and Limitations

1. Cloudflare Flexible SSL is transitional, not final production security.
2. Origin HTTPS on port 443 is not yet enabled.
3. HSTS is intentionally not enabled yet.
4. Production object storage is pending final setup.
5. SMTP/email delivery is not configured.
6. Real notification delivery is not implemented.
7. WebSockets/WSS are not implemented.
8. AI assistant is approved but not implemented.
9. Google Maps integration is approved but not implemented.
10. Payment workflows are not implemented.
11. Messaging is not implemented.
12. Vercel build should be treated as final build proof because local Windows/OneDrive builds can hang at trace collection.
13. Backend VPS deployment folder is not currently a Git checkout; future engineer may choose to convert it to a Git-based deployment, but must preserve `.env.production` and avoid touching Telehealth.

---

## 16. What the Engineer Should Do First

The incoming engineer should start with this sequence:

1. Clone both repos.
2. Confirm local setup works.
3. Check Vercel deployment status for latest frontend commit.
4. Confirm backend health endpoint.
5. Run frontend smoke test against live API.
6. Create a new branch for Sprint 6:

```bash
git checkout main
git pull origin main
git checkout -b feature/sprint-6-verification-layer
```

7. Write a short technical plan for Sprint 6 before coding.
8. Add backend verification models and migrations.
9. Add API endpoints and permissions.
10. Add frontend verification badge/status UI.
11. Add admin review screens.
12. Add tests.
13. Open a pull request into `main`.

---

## 17. PR Review Checklist

Every PR should answer:

1. Does it match the current sprint scope?
2. Does it avoid removed features like lawyer workflow?
3. Does it avoid future-sprint features unless explicitly approved?
4. Are backend permissions enforced?
5. Are object-level access checks tested?
6. Are migrations included and reversible?
7. Is the OpenAPI schema updated if endpoints changed?
8. Are frontend API contracts aligned with backend responses?
9. Are loading, empty, and error states handled?
10. Is demo mode still functional?
11. Does production mode avoid mock shortcuts?
12. Do lint/typecheck/tests pass?
13. Are screenshots attached for UI changes?
14. Are deployment notes clear?

---

## 18. Useful Commands

Backend:

```bash
ruff check .
pytest
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py spectacular --validate
```

Frontend:

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

RealityNG VPS:

```bash
ssh root@204.168.221.252
cd /opt/realityng/backend
docker compose -p realityng ps
docker compose -p realityng logs --tail=100 backend
curl -i http://127.0.0.1:18000/api/v1/health/
curl -i https://api.realityng.com/api/v1/health/
```

Do not run destructive Docker cleanup commands on the VPS.

---

## 19. Final Handoff Notes

The project is in a strong continuation position. The core marketplace transaction engine exists, the frontend has a branded conversion-oriented flow, the backend is reachable through Cloudflare HTTPS, and the next meaningful work is the trust and verification layer.

The engineer should preserve the current discipline:

1. Keep backend as source of truth for API contracts.
2. Keep demo mode isolated from production mode.
3. Keep each sprint scoped.
4. Use feature branches and PRs.
5. Avoid direct pushes to `main`.
6. Validate both frontend and backend before requesting review.
7. Never touch Telehealth infrastructure unless explicitly approved.
8. Do not expose secrets in GitHub, logs, screenshots, PRs, or reports.

