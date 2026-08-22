# RealityNG Consent Matrix

| Activity | Required? | Proof/version | Withdrawal | Current location/status |
|---|---|---|---|---|
| Account creation | Required operational action | Account timestamp | Account closure request | User model; exists |
| Terms acceptance | Required | `UserConsent`, Terms version, time, IP, agent | New use may stop; historical proof retained | Added Sprint 16 |
| Privacy acknowledgement | Required | `UserConsent`, notice version, time, IP, agent | Rights request; processing limits vary | Added Sprint 16 |
| Marketing | Optional | Separate channel/purpose/version | Self-service unsubscribe | Missing; do not market |
| Notifications | Operational required; preferences optional | Preference records | Settings by channel/type | Partial notification preferences |
| Analytics | Optional where required | Vendor/purpose/version | Preference control | Missing; non-essential analytics must remain off |
| Cookies | Essential vs optional separated | Consent record/version | Preference control | Missing; optional tracking must remain off |
| Financing application | User action | Application audit/timeline | Withdraw application where permitted | Exists |
| Financing data sharing | Required before sharing | `FinancingConsent`, scope, terms version, time, IP, agent | Revocation field exists; user flow missing | Partial; partner submission gated |
| Verification submission | Required action plus disclosure | Submission/audit record; policy version missing | Withdraw before decision where allowed | Partial |
| Inspection request | Required action plus disclosure | Request record; policy version missing | Cancel subject to policy | Partial |
| Private document upload | Required contextual acknowledgement | Upload/audit; disclosure version missing | Deletion request subject to exceptions | Partial |
| Escrow participation | Required before live use | No dedicated participation consent found | Contract/provider rules | Missing; live activation blocked |
| Complaint submission | Required action; evidence optional | Complaint record/audit | Correction/withdrawal subject to case integrity | Exists, version notice missing |

Required and optional choices must be separate, unambiguous, attributable, and purpose-specific. Financing consent must not authorize marketing or unrelated sharing. A user-facing financing-consent revocation route, escrow participation consent, cookie controls, and marketing proof **REQUIRE PROFESSIONAL REVIEW** before implementation/activation.

