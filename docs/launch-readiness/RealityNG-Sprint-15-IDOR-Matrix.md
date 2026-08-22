# RealityNG Sprint 15 Authorization and IDOR Matrix

Status: automated audit complete; browser-assisted persona validation pending

Legend: PASS = positive and negative automated evidence; REVIEW = covered by
permissions/querysets but requires expanded manual persona execution.

| Domain | Anonymous | Owner/subject | Related role | Unrelated user | Admin | Result |
| --- | --- | --- | --- | --- | --- | --- |
| Accounts/profiles/roles | Denied where protected | Scoped | Approved-role rules | Cross-user denied | Admin queue only | PASS |
| Properties/media | Public approved only | Manage own | Capability scoped | Mutation denied | Intended override | PASS |
| Assignments/leads | Denied | Owner | Active capability only | Denied | Allowed | PASS |
| Verification/documents | Denied | Own requests | N/A | Denied | Review authority | PASS |
| Inquiries/viewings/applications | Denied for actions | Participant | Participant only | Denied | Intended override | PASS |
| Services/quotes/bookings/reviews/complaints | Public safe subset | Customer/provider scoped | Owned provider only | Denied | Moderation only | PASS |
| Inspections/walkthroughs | Public approved walkthrough only | Owner/requester | Current inspector/capability | Denied | Allowed | PASS |
| Construction | Denied | Owner | Active stakeholder/capability | Denied | Allowed | PASS |
| Notifications/messaging | Denied | Recipient/participant | Thread participant | Denied | No implicit cross-thread access | PASS |
| Transactions/payment proofs/disputes | Denied | Buyer/owner | `manage_transactions` | Denied | Operations authority | PASS |
| Escrow | Denied | Participants | `manage_transactions` | Denied | Operations authority | PASS |
| Financing | Public products only | Applicant | No owner inheritance | Denied | Finance operations | PASS |

Methods reviewed include list, retrieve, create, patch, delete, custom actions,
signed URLs, moderation actions, and financial status transitions where each is
supported. Querysets generally fail closed with 404 for unrelated identifiers.

## Finding S15-AUTH-001

- Domain: inspections
- Severity: HIGH
- Description: historical declined/cancelled/reassigned inspection assignments
  remained visible to the former inspector, and the shared access helper treated
  any historical assignment as authorization.
- Affected persona: inspector/former inspector
- Security impact: continued access to private inspection request data after
  assignment authority ended.
- Reproduction: change an assignment to declined, cancelled, or reassigned and
  retrieve its assignment/request identifiers as the former inspector.
- Expected: 404/denied.
- Actual before fix: assignment filtering was unrestricted; request filtering
  trusted the stale `assigned_inspector` field.
- Fix: define explicit access-bearing statuses (`assigned`, `accepted`,
  `completed`) and use them in both request and assignment querysets.
- Regression: parameterized negative API test for all three inactive statuses.

