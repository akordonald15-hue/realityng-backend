# RealityNG Inspection Permission Matrix

| Actor | Inspection Requests | Assignments | Walkthroughs | Reports | Evidence | Admin Moderation |
| --- | --- | --- | --- | --- | --- | --- |
| Anonymous | None | None | View approved public walkthroughs | None | None | None |
| Authenticated customer | Create for approved properties they do not own; view own requests | None | View approved public walkthroughs | View approved reports for own request | View requester-visible evidence through signed URLs | None |
| Property owner landlord/agent | Cannot request inspection for own property | None | Upload/manage own property walkthroughs; submit for moderation | View approved reports for their property | View owner-visible evidence through signed URLs | None |
| Approved inspector | View assigned requests | Accept/decline own assignments | View approved public walkthroughs | Create/submit reports for assigned requests | Upload own report evidence | None |
| Admin | View all | Assign inspectors | Moderate all walkthroughs | Review all reports | Access authorized signed evidence | Full inspection moderation |
| Suspended/inactive user | Blocked from new requests and uploads | None | Public-only access where unauthenticated access is allowed | None | None | None |

## High-Risk Rules

- A user cannot request an inspection for their own property.
- A customer cannot view another customer's request.
- A non-owner cannot upload walkthroughs without a future managed-property relationship.
- Inspectors can create reports only for assigned requests.
- Evidence signed URLs require backend permission checks.
- Admin endpoints require admin permissions and must not rely on frontend route protection.
