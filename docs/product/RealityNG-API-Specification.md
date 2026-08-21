# RealityNG REST API Specification

Version: 1.0  
Date: 2026-06-16  
Base URL: `/api/v1/`  
Source: RealityNG PRD v1.0

## 1. API Standards

Authentication:

1. Public endpoints allow anonymous access only where explicitly stated.
2. Authenticated web calls use secure cookie-backed auth or bearer token depending on deployment.
3. Mobile later uses bearer JWT access token and refresh token rotation.
4. Admin and specialist endpoints require MFA-backed sessions.

Common headers:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
Idempotency-Key: <uuid>   # required for payment, booking, upload, and webhook-sensitive creates
```

Pagination response:

```json
{
  "count": 120,
  "next": "/api/v1/properties/?page=2",
  "previous": null,
  "results": []
}
```

Error response:

```json
{
  "error": {
    "code": "validation_error",
    "message": "One or more fields are invalid.",
    "fields": {
      "price_minor": ["Must be greater than 0."]
    }
  }
}
```

Common errors: `400 validation_error`, `401 not_authenticated`, `403 permission_denied`, `404 not_found`, `409 invalid_state`, `409 duplicate`, `429 rate_limited`, `500 server_error`.

## 2. Auth

| Method | URL | Purpose | Auth | Permission | Request Example | Response Example | Errors | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| POST | `/auth/register/` | Create user account | Public | none | `{"email":"ada@example.com","phone":"+2348010000000","password":"Str0ngPass!","roles":["buyer"]}` | `{"id":"usr_1","email":"ada@example.com","status":"pending_verification"}` | 400,409,429 | Sends verification email/OTP. |
| POST | `/auth/login/` | Login | Public | none | `{"email":"ada@example.com","password":"Str0ngPass!"}` | `{"access":"jwt","refresh":"jwt","user":{"id":"usr_1","roles":["buyer"]}}` | 400,401,429 | Admin login may require MFA challenge. |
| POST | `/auth/refresh/` | Rotate token | Public | valid refresh | `{"refresh":"jwt"}` | `{"access":"jwt","refresh":"jwt"}` | 401,409 | Reuse detection revokes token family. |
| POST | `/auth/logout/` | Revoke current session/token | Required | self | `{}` | `{"status":"ok"}` | 401 | Clears web cookie where applicable. |
| POST | `/auth/verify-email/` | Verify email | Public | token | `{"token":"email-token"}` | `{"email_verified":true}` | 400,404 | Token expires. |
| POST | `/auth/request-otp/` | Request phone OTP | Required | self | `{"phone":"+2348010000000"}` | `{"status":"sent"}` | 400,429 | Rate limited. |
| POST | `/auth/verify-otp/` | Verify phone OTP | Required | self | `{"phone":"+2348010000000","code":"123456"}` | `{"phone_verified":true}` | 400,429 | Required for high-risk workflows. |
| POST | `/auth/password-reset/` | Request reset | Public | none | `{"email":"ada@example.com"}` | `{"status":"sent_if_exists"}` | 429 | Do not reveal account existence. |
| POST | `/auth/password-reset/confirm/` | Confirm reset | Public | token | `{"token":"reset-token","password":"NewStr0ng!"}` | `{"status":"ok"}` | 400 | Invalidates active sessions. |
| GET | `/auth/me/` | Current user | Required | self | none | `{"id":"usr_1","email":"ada@example.com","roles":["buyer"]}` | 401 | Used by web app bootstrap. |

## 3. Users and Roles

| Method | URL | Purpose | Auth | Permission | Request Example | Response Example | Errors | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/users/me/` | Get own profile | Required | self | none | `{"id":"usr_1","profile":{"display_name":"Ada"}}` | 401 | Includes profile and roles. |
| PATCH | `/users/me/` | Update own profile | Required | self | `{"profile":{"display_name":"Ada Okafor","country":"United Kingdom"}}` | `{"id":"usr_1","profile":{"display_name":"Ada Okafor"}}` | 400,401 | Cannot self-assign admin role. |
| GET | `/users/{id}/` | Get user public/admin profile | Required | participant/admin | none | `{"id":"usr_2","display_name":"Prime Agent","verification_status":"verified"}` | 403,404 | Public response redacts sensitive fields. |
| POST | `/roles/request/` | Request an additional role | Required | self | `{"role":"agent","reason":"I manage listings"}` | `{"role":"agent","status":"pending"}` | 400,409 | Professional roles require approval. |
| GET | `/roles/` | List role catalog | Required | any | none | `{"results":[{"code":"buyer","name":"Buyer"}]}` | 401 | Used by role setup. |
| GET | `/admin/users/` | Admin user search | Required | admin | none | `{"results":[{"id":"usr_1","status":"active"}]}` | 403 | Supports filters. |
| PATCH | `/admin/users/{id}/status/` | Restrict/suspend user | Required | admin | `{"status":"suspended","reason":"Fraud reports"}` | `{"id":"usr_1","status":"suspended"}` | 400,403,409 | Writes audit log. |
| PATCH | `/admin/users/{id}/roles/{role}/` | Approve/revoke role | Required | admin | `{"status":"active","reason":"Docs approved"}` | `{"role":"agent","status":"active"}` | 403,404 | Super admin required for admin roles. |

## 4. Properties

| Method | URL | Purpose | Auth | Permission | Request Example | Response Example | Errors | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/properties/` | Browse/search public listings | Public | none | query params | `{"count":2,"results":[{"id":"prop_1","title":"4 Bedroom Duplex","price_minor":120000000,"verification_status":"verified"}]}` | 400 | Filters: location, category, price, beds, maps bounds. |
| POST | `/properties/` | Create listing draft | Required | landlord/agent/admin | `{"category":"sale","property_type":"duplex","title":"4 Bedroom Duplex","price_minor":120000000,"currency":"NGN","state":"Lagos","city":"Lekki"}` | `{"id":"prop_1","status":"draft"}` | 400,403 | Owner defaults to creator unless agent specifies authorization. |
| GET | `/properties/{id}/` | Property detail | Public | none | none | `{"id":"prop_1","title":"4 Bedroom Duplex","media":[],"trust":{"property":"verified"}}` | 404 | Private fields redacted unless authorized. |
| PATCH | `/properties/{id}/` | Update listing | Required | owner/agent/admin | `{"price_minor":115000000,"description":"Updated description"}` | `{"id":"prop_1","status":"draft"}` | 400,403,409 | Material edits may require re-approval. |
| DELETE | `/properties/{id}/` | Archive listing | Required | owner/agent/admin | `{}` | `{"status":"archived"}` | 403,404 | Soft delete/archive only. |
| POST | `/properties/{id}/submit/` | Submit for approval | Required | owner/agent | `{}` | `{"id":"prop_1","status":"submitted"}` | 400,403,409 | Requires media and required fields. |
| POST | `/properties/{id}/media/` | Attach media document | Required | owner/agent/admin | `{"document_id":"doc_1","media_type":"image","sort_order":1,"is_cover":true}` | `{"id":"media_1"}` | 400,403 | Document must be uploaded and accessible. |
| GET | `/properties/{id}/documents/` | List authorized property documents | Required | owner/agent/requester/specialist/admin | none | `{"results":[{"id":"doc_1","document_type":"survey"}]}` | 403 | Sensitive docs are never public. |
| POST | `/admin/properties/{id}/approve/` | Approve listing | Required | admin | `{"decision_note":"Meets policy"}` | `{"id":"prop_1","status":"approved"}` | 403,409 | Writes audit log. |
| POST | `/admin/properties/{id}/reject/` | Reject listing | Required | admin | `{"reason":"Missing ownership evidence"}` | `{"id":"prop_1","status":"rejected"}` | 400,403 | Notifies owner/agent. |

## 5. Favorites, Saved Searches, Comparisons

| Method | URL | Purpose | Auth | Permission | Request Example | Response Example | Errors | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/favorites/` | List favorites | Required | self | none | `{"results":[{"property_id":"prop_1"}]}` | 401 | User dashboard. |
| POST | `/favorites/` | Favorite property | Required | self | `{"property_id":"prop_1"}` | `{"id":"fav_1","property_id":"prop_1"}` | 400,404,409 | Unique per user/property. |
| DELETE | `/favorites/{property_id}/` | Remove favorite | Required | self | `{}` | `{"status":"removed"}` | 404 | Soft delete. |
| GET | `/saved-searches/` | List saved searches | Required | self | none | `{"results":[{"id":"ss_1","name":"Lekki land"}]}` | 401 |  |
| POST | `/saved-searches/` | Create saved search | Required | self | `{"name":"Lekki land","filters":{"category":"land","state":"Lagos"},"alert_frequency":"daily"}` | `{"id":"ss_1","is_active":true}` | 400 | Alerts generated by Celery. |
| PATCH | `/saved-searches/{id}/` | Update saved search | Required | owner | `{"alert_frequency":"weekly","is_active":false}` | `{"id":"ss_1","is_active":false}` | 403,404 |  |
| DELETE | `/saved-searches/{id}/` | Delete saved search | Required | owner | `{}` | `{"status":"deleted"}` | 403,404 | Soft delete. |
| POST | `/comparisons/` | Persist comparison set | Required | self | `{"property_ids":["prop_1","prop_2"]}` | `{"id":"cmp_1","property_ids":["prop_1","prop_2"]}` | 400 | Limit 2-4 properties. |
| GET | `/comparisons/preview/` | Compare properties without saving | Public | none | query `property_ids=prop_1,prop_2` | `{"properties":[{"id":"prop_1","price_minor":120000000}]}` | 400,404 | Public fields only for guests. |

## 6. Viewings and Applications

| Method | URL | Purpose | Auth | Permission | Request Example | Response Example | Errors | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/viewings/` | List relevant viewings | Required | participant/admin | none | `{"results":[{"id":"view_1","status":"requested"}]}` | 401 | Filters by role. |
| POST | `/viewings/` | Request viewing | Required | verified user | `{"property_id":"prop_1","preferred_slots":["2026-07-01T10:00:00Z"],"meeting_type":"physical"}` | `{"id":"view_1","status":"requested"}` | 400,403,409 | Property must be active. |
| PATCH | `/viewings/{id}/` | Respond/reschedule | Required | requester/host/admin | `{"status":"accepted","scheduled_at":"2026-07-01T10:00:00Z"}` | `{"id":"view_1","status":"accepted"}` | 400,403,409 | Invalid transitions rejected. |
| POST | `/viewings/{id}/complete/` | Mark completed | Required | host/admin | `{"notes":"Completed"}` | `{"id":"view_1","status":"completed"}` | 403,409 |  |
| GET | `/applications/` | List applications | Required | applicant/listing owner/admin | none | `{"results":[{"id":"app_1","status":"submitted"}]}` | 401 | Role-filtered. |
| POST | `/applications/` | Create/submit application | Required | tenant/buyer | `{"property_id":"prop_1","answers":{"occupation":"Engineer"}}` | `{"id":"app_1","status":"submitted"}` | 400,403,409 | Rental properties only for MVP. |
| GET | `/applications/{id}/` | Application detail | Required | applicant/owner/admin | none | `{"id":"app_1","answers":{"occupation":"Engineer"}}` | 403,404 | Sensitive fields redacted by role. |
| PATCH | `/applications/{id}/` | Update draft application | Required | applicant | `{"answers":{"occupation":"Product Manager"}}` | `{"id":"app_1","status":"draft"}` | 400,403,409 | Submitted applications require withdrawal/reapply policy. |
| POST | `/applications/{id}/decision/` | Approve/reject application | Required | listing owner/admin | `{"decision":"approved","reason":"Meets requirements"}` | `{"id":"app_1","status":"approved"}` | 400,403,409 | Writes audit log. |

## 7. Artisans and Service Bookings

| Method | URL | Purpose | Auth | Permission | Request Example | Response Example | Errors | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/artisans/` | Browse artisans | Public | none | query params | `{"results":[{"id":"art_1","business_name":"Prime Plumbing","rating_avg":"4.80"}]}` | 400 | Only approved profiles. |
| POST | `/artisans/` | Create artisan profile | Required | artisan | `{"business_name":"Prime Plumbing","category":"plumber","service_locations":["Lagos"]}` | `{"id":"art_1","profile_status":"draft"}` | 400,403,409 | One profile per user. |
| GET | `/artisans/{id}/` | Artisan detail | Public | none | none | `{"id":"art_1","portfolio":[],"verification_status":"verified"}` | 404 | Public profile only if approved. |
| PATCH | `/artisans/{id}/` | Update own profile | Required | owner/admin | `{"bio":"10 years experience","service_locations":["Lagos","Ogun"]}` | `{"id":"art_1"}` | 400,403 | Material changes may trigger review. |
| POST | `/artisans/{id}/submit/` | Submit profile for approval | Required | owner | `{}` | `{"id":"art_1","profile_status":"submitted"}` | 400,403 | Requires portfolio/basic fields. |
| GET | `/service-bookings/` | List bookings | Required | customer/artisan/admin | none | `{"results":[{"id":"sb_1","status":"requested"}]}` | 401 | Role-filtered. |
| POST | `/service-bookings/` | Request artisan service | Required | user | `{"artisan_id":"art_1","service_category":"plumber","description":"Fix leak","preferred_slots":["2026-07-03T09:00:00Z"]}` | `{"id":"sb_1","status":"requested"}` | 400,403 | Artisan must be approved. |
| PATCH | `/service-bookings/{id}/` | Quote/schedule/update booking | Required | customer/artisan/admin | `{"status":"quoted","quote_amount_minor":500000,"currency":"NGN"}` | `{"id":"sb_1","status":"quoted"}` | 400,403,409 | Status transitions enforced. |
| POST | `/service-bookings/{id}/complete/` | Complete job | Required | artisan/customer/admin | `{"completion_note":"Completed"}` | `{"id":"sb_1","status":"completed"}` | 403,409 | Enables review. |
| POST | `/reviews/` | Review completed service/entity | Required | participant | `{"target_entity_type":"artisan","target_entity_id":"art_1","booking_id":"sb_1","rating":5,"comment":"Great work"}` | `{"id":"rev_1","status":"published"}` | 400,403,409 | One review per completed booking. |

## 8. Verification, Legal, and Inspection

| Method | URL | Purpose | Auth | Permission | Request Example | Response Example | Errors | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/verification-requests/` | List verification requests | Required | requester/assignee/admin | none | `{"results":[{"id":"ver_1","status":"under_review"}]}` | 401 | Role-filtered. |
| POST | `/verification-requests/` | Create verification request | Required | authorized target owner | `{"type":"property","target_entity_type":"property","target_entity_id":"prop_1"}` | `{"id":"ver_1","status":"submitted"}` | 400,403,409 | Required docs vary by type. |
| PATCH | `/verification-requests/{id}/` | Add info/update draft | Required | requester/admin | `{"notes":"Uploaded survey plan"}` | `{"id":"ver_1","status":"submitted"}` | 400,403,409 | Cannot edit after final decision except admin reopen. |
| POST | `/admin/verification-requests/{id}/assign/` | Assign reviewer | Required | admin | `{"assignee_id":"usr_lawyer_or_admin"}` | `{"id":"ver_1","status":"assigned"}` | 403,409 | Writes audit log. |
| POST | `/admin/verification-requests/{id}/decision/` | Decide request | Required | admin | `{"decision":"verified","reason":"Ownership confirmed","expires_at":"2027-06-16T00:00:00Z"}` | `{"id":"ver_1","status":"verified"}` | 400,403,409 | Updates public badge where applicable. |
| GET | `/legal-reviews/` | List legal reviews | Required | requester/lawyer/admin | none | `{"results":[{"id":"lr_1","status":"assigned"}]}` | 401 |  |
| POST | `/legal-reviews/` | Request legal review | Required | buyer/requester | `{"property_id":"prop_1","questions":"Confirm title risks"}` | `{"id":"lr_1","status":"submitted"}` | 400,403 | Creates document checklist. |
| PATCH | `/legal-reviews/{id}/` | Update review/request docs | Required | requester/lawyer/admin | `{"questions":"Also review survey plan"}` | `{"id":"lr_1"}` | 403,409 | Final opinions versioned. |
| POST | `/admin/legal-reviews/{id}/assign/` | Assign lawyer | Required | admin | `{"lawyer_id":"usr_lawyer"}` | `{"id":"lr_1","status":"assigned"}` | 403,409 | Lawyer must be approved. |
| POST | `/legal-reviews/{id}/opinion/` | Issue legal opinion | Required | assigned lawyer/admin | `{"risk_level":"medium","opinion_summary":"Proceed only after seller provides original deed."}` | `{"id":"lr_1","status":"opinion_issued"}` | 400,403,409 | Immutable/versioned after issue. |
| GET | `/inspection-requests/` | List inspections | Required | requester/inspector/admin | none | `{"results":[{"id":"ir_1","status":"scheduled"}]}` | 401 |  |
| POST | `/inspection-requests/` | Request inspection | Required | user | `{"type":"property","property_id":"prop_1","scope":"Purchase inspection","preferred_slots":["2026-07-04T08:00:00Z"]}` | `{"id":"ir_1","status":"requested"}` | 400,403 | Type: property, construction, site_visit. |
| POST | `/admin/inspection-requests/{id}/assign/` | Assign inspector | Required | admin | `{"inspector_id":"usr_inspector","scheduled_at":"2026-07-04T08:00:00Z"}` | `{"id":"ir_1","status":"scheduled"}` | 403,409 | Inspector must be approved and conflict-free. |
| POST | `/inspection-reports/` | Submit report | Required | assigned inspector | `{"inspection_request_id":"ir_1","recommendation":"proceed_with_caution","summary":"Roof leakage observed.","checklist":{"location_confirmed":true}}` | `{"id":"rep_1","status":"submitted"}` | 400,403,409 | Requires evidence documents before release. |
| POST | `/admin/inspection-reports/{id}/release/` | Release report to requester | Required | admin | `{"decision_note":"QA complete"}` | `{"id":"rep_1","status":"released"}` | 403,409 | Notifies requester. |

## 9. Construction and Payment Milestones

| Method | URL | Purpose | Auth | Permission | Request Example | Response Example | Errors | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/construction-projects/` | List projects | Required | owner/assigned/admin | none | `{"results":[{"id":"cp_1","status":"active"}]}` | 401 |  |
| POST | `/construction-projects/` | Create project | Required | owner/buyer/admin | `{"name":"Lekki Duplex Build","property_id":"prop_1","project_type":"new_build","budget_amount_minor":8000000000,"currency":"NGN"}` | `{"id":"cp_1","status":"draft"}` | 400,403 | Can use milestone template. |
| GET | `/construction-projects/{id}/` | Project detail | Required | owner/assigned/admin | none | `{"id":"cp_1","milestones":[]}` | 403,404 |  |
| PATCH | `/construction-projects/{id}/` | Update project | Required | owner/admin | `{"target_end_date":"2027-03-30"}` | `{"id":"cp_1"}` | 400,403 | Approved milestones constrain edits. |
| POST | `/project-milestones/` | Create milestone | Required | project owner/admin | `{"project_id":"cp_1","name":"Foundation","scope":"Excavation and concrete works","due_date":"2026-08-01"}` | `{"id":"pm_1","status":"not_started"}` | 400,403 | Default template can pre-create milestones. |
| PATCH | `/project-milestones/{id}/` | Update milestone progress | Required | owner/assigned/admin | `{"status":"in_progress","progress_percent":40}` | `{"id":"pm_1","progress_percent":40}` | 400,403,409 | Approval requires inspection/admin rule. |
| POST | `/project-milestones/{id}/submit-inspection/` | Submit milestone for inspection | Required | project owner/admin | `{}` | `{"id":"pm_1","status":"submitted_for_inspection"}` | 403,409 | Can create linked inspection request. |
| GET | `/payment-milestones/` | List payment milestones | Required | payer/payee/admin | none | `{"results":[{"id":"pay_1","status":"pending"}]}` | 401 | Role-filtered. |
| POST | `/payment-milestones/` | Create payment milestone | Required | authorized participant/admin | `{"related_entity_type":"project_milestone","related_entity_id":"pm_1","payer_id":"usr_1","payee_id":"usr_2","amount_minor":1000000000,"currency":"NGN","due_date":"2026-08-03"}` | `{"id":"pay_1","status":"pending"}` | 400,403 | Does not mean RealityNG holds funds. |
| POST | `/payment-milestones/{id}/proof/` | Upload proof reference | Required | payer/admin | `{"document_id":"doc_1","note":"Bank transfer receipt"}` | `{"id":"pay_1","status":"proof_uploaded"}` | 400,403,409 | Creates PaymentEvent. |
| POST | `/admin/payment-milestones/{id}/decision/` | Approve/reject proof/status | Required | admin | `{"decision":"approved","reason":"Receipt confirmed"}` | `{"id":"pay_1","status":"approved"}` | 400,403,409 | Appends PaymentEvent and audit log. |

## 10. Documents

| Method | URL | Purpose | Auth | Permission | Request Example | Response Example | Errors | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| POST | `/documents/upload-intents/` | Create signed upload URL | Required | entity access | `{"entity_type":"property","entity_id":"prop_1","document_type":"image","filename":"front.jpg","content_type":"image/jpeg","size_bytes":900000}` | `{"document_id":"doc_1","upload_url":"https://signed-upload","headers":{}}` | 400,403,429 | Creates pending Document. |
| POST | `/documents/{id}/complete/` | Mark upload complete | Required | uploader/admin | `{"checksum":"sha256:abc"}` | `{"id":"doc_1","status":"processing"}` | 400,403,409 | Queues scan/processing. |
| GET | `/documents/{id}/download-url/` | Get signed read URL | Required | authorized reader | none | `{"url":"https://signed-read","expires_in":300}` | 403,404 | Sensitive docs require audit log. |
| DELETE | `/documents/{id}/` | Soft delete document | Required | uploader/entity owner/admin | `{}` | `{"status":"deleted"}` | 403,404,409 | Cannot delete if legally locked; admin can revoke visibility. |

## 11. Disputes and Notifications

| Method | URL | Purpose | Auth | Permission | Request Example | Response Example | Errors | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/disputes/` | List disputes | Required | party/admin | none | `{"results":[{"id":"dis_1","status":"open"}]}` | 401 | Role-filtered. |
| POST | `/disputes/` | Open dispute | Required | related participant | `{"related_entity_type":"payment_milestone","related_entity_id":"pay_1","category":"payment","description":"Proof rejected incorrectly"}` | `{"id":"dis_1","status":"open"}` | 400,403 | Locks sensitive workflows where required. |
| PATCH | `/disputes/{id}/` | Add response/update dispute | Required | party/admin | `{"description":"Additional evidence uploaded"}` | `{"id":"dis_1","status":"under_review"}` | 400,403,409 | Major transitions admin-only. |
| POST | `/admin/disputes/{id}/resolve/` | Resolve dispute | Required | admin | `{"resolution":"Payment proof accepted","outcome":"resolved"}` | `{"id":"dis_1","status":"resolved"}` | 400,403,409 | Audit log required. |
| GET | `/notifications/` | List notifications | Required | self | none | `{"results":[{"id":"not_1","title":"Inspection released","read_at":null}]}` | 401 | Supports unread filter. |
| POST | `/notifications/{id}/read/` | Mark read | Required | owner | `{}` | `{"id":"not_1","read_at":"2026-06-16T12:00:00Z"}` | 403,404 |  |
| POST | `/notifications/read-all/` | Mark all read | Required | self | `{}` | `{"updated":12}` | 401 |  |

## 12. Admin Operations

| Method | URL | Purpose | Auth | Permission | Request Example | Response Example | Errors | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GET | `/admin/dashboard/` | Admin metrics and queues | Required | admin | none | `{"queues":{"properties":4,"verification":8,"inspection":2}}` | 403 | No PII-heavy payload. |
| GET | `/admin/approvals/` | Unified approval queue | Required | admin | query params | `{"results":[{"entity_type":"property","entity_id":"prop_1","status":"submitted"}]}` | 403 | Filters by type/status. |
| POST | `/admin/assignments/` | Create/reassign operational assignment | Required | admin | `{"entity_type":"legal_review","entity_id":"lr_1","assignee_id":"usr_lawyer","reason":"Availability"}` | `{"status":"assigned"}` | 400,403,409 | Writes audit log. |
| GET | `/admin/audit-logs/` | Search audit logs | Required | admin | query params | `{"results":[{"actor_id":"usr_1","action":"property.approve"}]}` | 403 | Super admin can export. |
| GET | `/admin/webhook-events/` | List webhook processing state | Required | admin | query params | `{"results":[{"id":"wh_1","processing_status":"failed"}]}` | 403 | For payment/provider support. |
| POST | `/admin/webhook-events/{id}/replay/` | Replay failed webhook | Required | admin | `{"reason":"Provider timeout fixed"}` | `{"id":"wh_1","processing_status":"processing"}` | 403,409 | Idempotent processing required. |
| GET | `/admin/system-health/` | Operational health summary | Required | admin | none | `{"celery":{"failed":0},"providers":{"paystack":"ok"}}` | 403 | Aggregates internal checks. |

## 13. Webhooks

| Method | URL | Purpose | Auth | Permission | Request Example | Response Example | Errors | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| POST | `/webhooks/paystack/` | Paystack webhook intake | Provider signature | valid signature | provider payload | `{"received":true}` | 400,401 | Store raw payload before processing. |
| POST | `/webhooks/flutterwave/` | Flutterwave webhook intake | Provider signature | valid signature | provider payload | `{"received":true}` | 400,401 | Idempotent by provider event id. |
| POST | `/webhooks/stripe/` | Stripe webhook intake | Provider signature | valid signature | provider payload | `{"received":true}` | 400,401 | Never trust client-side payment status. |

