# RealityNG Sprint 9.6 - Governance and Moderation Report

## Executive Summary

Sprint 9.6 adds the operational governance layer for the verified services marketplace. It introduces complaint management, provider warnings, temporary/permanent suspensions, provider appeals, admin moderation queues, and audit coverage while preserving Sprint 9.1-9.5 marketplace, profile, quote, review, dashboard, maps fallback, assistant, and property workflows.

## Architecture

The implementation extends `apps.services` instead of creating a parallel governance app. Complaints, evidence, and appeals are linked to `ServiceProvider` and can optionally reference quote requests, bookings, or reviews. Provider moderation state remains on `ServiceProvider` so public marketplace filtering and owner dashboards can enforce restrictions consistently.

## Models and Migration

Migration: `apps/services/migrations/0007_providerappeal_servicecomplaint_and_more.py`

Added:

- `ServiceComplaint`
- `ServiceComplaintEvidence`
- `ProviderAppeal`

Extended:

- `ServiceProvider.warning_count`
- `ServiceProvider.last_warning_reason`
- `ServiceProvider.suspension_type`
- `ServiceProvider.suspension_expires_at`
- `ServiceProvider.appeal_status`

## Complaint Workflow

Statuses:

- `open`
- `under_review`
- `awaiting_customer`
- `awaiting_provider`
- `resolved`
- `rejected`
- `escalated`
- `closed`

Customers can create and view their own complaints. Providers can view complaints linked to their provider profile. Admins can review, resolve, reject, escalate, close, or request more information from either party.

## Suspension Workflow

Admins can warn, suspend, and reactivate providers. Suspended providers are removed from public marketplace visibility, cannot receive new quote requests, cannot edit profile data, cannot advance quote-request status, and cannot respond to reviews. Historical data remains intact.

## Appeals

Providers can submit warning or suspension appeals. Admins can approve, reject, or reopen appeals. Approved suspension appeals reactivate the provider through the existing provider lifecycle.

## API Endpoints

Customer:

- `GET /api/v1/services/complaints/`
- `POST /api/v1/services/complaints/`
- `GET /api/v1/services/complaints/{id}/`
- `POST /api/v1/services/complaints/{id}/evidence/`

Provider:

- `GET /api/v1/services/provider-profile/complaints/`
- `GET /api/v1/services/provider-profile/complaints/{id}/`
- `GET /api/v1/services/provider-profile/appeals/`
- `POST /api/v1/services/provider-profile/appeals/`
- `GET /api/v1/services/provider-profile/appeals/{id}/`

Admin:

- `GET /api/v1/services/admin/complaints/`
- `GET /api/v1/services/admin/complaints/{id}/`
- `POST /api/v1/services/admin/complaints/{id}/review/`
- `POST /api/v1/services/admin/complaints/{id}/resolve/`
- `POST /api/v1/services/admin/complaints/{id}/reject/`
- `POST /api/v1/services/admin/complaints/{id}/escalate/`
- `POST /api/v1/services/admin/complaints/{id}/close/`
- `POST /api/v1/services/admin/complaints/{id}/await-customer/`
- `POST /api/v1/services/admin/complaints/{id}/await-provider/`
- `GET /api/v1/services/admin/appeals/`
- `GET /api/v1/services/admin/appeals/{id}/`
- `POST /api/v1/services/admin/appeals/{id}/approve/`
- `POST /api/v1/services/admin/appeals/{id}/reject/`
- `POST /api/v1/services/admin/appeals/{id}/reopen/`
- `POST /api/v1/services/admin/providers/{id}/warn/`
- `POST /api/v1/services/admin/providers/{id}/suspend/`
- `POST /api/v1/services/admin/providers/{id}/reactivate/`

## Permissions

- Customers only see their own complaints.
- Providers only see complaints and appeals tied to their own provider profile.
- Admin governance endpoints require services-admin permissions.
- Providers cannot approve, reactivate, or moderate themselves.
- Suspended providers remain unable to mutate restricted marketplace actions.

## Audit Events

Added events include:

- `service_complaint.created`
- `service_complaint.evidence_uploaded`
- `service_complaint.under_review`
- `service_complaint.resolved`
- `service_complaint.rejected`
- `service_complaint.escalated`
- `service_complaint.closed`
- `service_provider.warned`
- `service_provider.suspended`
- `service_provider.reactivated`
- `service_provider.appeal_submitted`
- `service_provider.appeal_approved`
- `service_provider.appeal_rejected`
- `service_provider.appeal_reopened`

## Security Notes

The sprint preserves object-level permissions and public/private serializer separation. Complaint evidence is only exposed through authenticated complaint serializers, not public provider profiles. Suspended providers are excluded by the existing active-provider public queryset.

## Validation

Target validation:

- `ruff check .`
- `python manage.py check`
- `python manage.py makemigrations --check --dry-run`
- `python manage.py migrate --noinput`
- `python manage.py spectacular --validate`
- `pytest apps/services/tests -q`
- `pytest -q`

## Known Limitations

- Evidence storage uses the existing backend media mechanism and should be moved to a private moderation bucket before high-volume production complaint evidence.
- Notification delivery is not implemented.
- Messaging between customer, provider, and admin is not implemented.
- Complaint analytics are intentionally deferred.

## Sprint 9.7 Readiness

Sprint 9.7 can build on this foundation for reporting, moderation analytics, governance notifications, or escalation workflows without changing the core complaint and appeal models.
