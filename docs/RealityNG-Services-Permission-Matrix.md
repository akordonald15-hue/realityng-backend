# RealityNG Services Marketplace Permission Matrix

This matrix covers the Sprint 9.1-9.7 services marketplace baseline. Backend object-level permissions remain authoritative; frontend route guards are only a usability layer.

Legend:

- `R`: read/list/retrieve
- `C`: create/upload
- `U`: update metadata or mutable fields
- `T`: transition workflow status
- `D`: delete/archive
- `M`: moderate/admin decision
- `No`: not permitted

| Surface / endpoint family | Anonymous | Customer | Provider | Suspended Provider | Property Owner / Agent | Admin |
| --- | --- | --- | --- | --- | --- | --- |
| `/services/categories/` | R | R | R | R | R | R/M via admin tooling |
| `/services/providers/` public list/detail | R active only | R active only | R active only | Own profile is not public | R active only | R all through admin endpoints |
| `/services/provider-profile/` | No | No | C once if eligible | No | C if eligible agent role | M through admin endpoints |
| `/services/provider-profile/me/` | No | No | R/U own if not suspended/archived | R only | R/U own if eligible and not suspended/archived | R/M through admin endpoints |
| `/services/provider-profile/submit/` | No | No | T own draft/rejected/more-info profile | No | T own eligible profile | M through admin endpoints |
| `/services/provider-profile/deactivate/` | No | No | T own active profile | No | T own active profile | M through admin endpoints |
| Provider trades | No | No | R/C/U/D own if not suspended/archived | R own only | R/C/U/D own if eligible and not suspended/archived | R/M through provider admin |
| Provider service areas | No | No | R/C/U/D own if not suspended/archived | R own only | R/C/U/D own if eligible and not suspended/archived | R/M through provider admin |
| Provider portfolio | No | No | R/C/U/D/reorder/cover own if not suspended/archived | R own only | R/C/U/D own if eligible and not suspended/archived | R/M through provider admin |
| Public quote request create | C against active providers | C against active providers | C as customer only, not to self | No because provider is hidden/inactive publicly | C as customer only, not to self | C for testing only; M via admin queue |
| Customer quote history/dashboard | No | R own | R own customer requests | R own customer requests | R own customer requests | M through admin queue |
| Provider quote management | No | No | R own, T own if active | R own only; no status transitions | R/T own if provider role active | R/T through admin queue |
| Service bookings | No | R own when exposed through dashboard/review eligibility | R own provider bookings | R own only | R own provider bookings | M through admin/ops tooling |
| Customer reviews | No | C/R/U own eligible booking within edit policy | No self-review | No self-review | No self-review | M through admin reviews |
| Public provider reviews | R published only | R published only | R published only | Provider hidden publicly | R published only | R all through admin endpoints |
| Provider review responses | No | No | T/respond once to own published review if active | No | T/respond if active provider profile | M through admin reviews |
| Review flags | No | C own authenticated flag | C own authenticated flag | C own authenticated flag | C own authenticated flag | M through admin reviews |
| Customer complaints | No | C/R own | C/R own when provider participant | C/R own; no profile mutation | C/R own when participant | M through admin complaints |
| Complaint evidence | No | C/R metadata own complaint only | C/R metadata linked to own profile/complaint | C/R metadata own complaint only | C/R metadata own complaint only | R/M metadata through admin complaints |
| Provider complaints | No | No | R complaints linked to own provider profile | R complaints linked to own provider profile | R own provider complaints | M through admin complaints |
| Provider appeals | No | No | C/R own warning or suspension appeals | C/R own suspension appeals | C/R own eligible provider appeals | M approve/reject/reopen |
| Provider warning/suspension/reactivation | No | No | No self-moderation | No | No | M admin-only, self-review blocked |
| Services customer dashboard | No | R own | R own customer data | R own customer data | R own customer data | R/M global via admin dashboard |
| Services provider dashboard | No | No | R own provider summary | R own with restriction banner | R own provider summary | R/M global via admin dashboard |
| Services admin dashboard | No | No | No | No | No | R/M admin-only |

## High-Risk Cases Automated

- Non-admin users cannot access admin dashboard and moderation endpoints.
- Customers cannot see another customer's complaint list.
- Providers cannot manage quote status while suspended.
- Providers cannot respond to reviews while suspended.
- Suspended providers cannot patch provider profile data.
- Suspended providers cannot mutate trades, service areas, or portfolio.
- Public provider discovery excludes suspended providers.
- Public reviews exclude hidden, flagged, removed, and unpublished reviews.
- Customer review creation requires a completed booking and one review per booking.
- Complaint evidence upload rejects invalid content and does not serialize permanent file paths or public URLs.

## Deferred Manual/Staging Checks

- Browser validation of every role combination should be repeated in a staging or preview environment before a public beta release.
- Complaint evidence download should use a future private signed-download flow if operations needs file inspection in the web UI.
- Production bucket policies must be checked directly in MinIO/S3 before enabling high-volume complaint evidence uploads.
