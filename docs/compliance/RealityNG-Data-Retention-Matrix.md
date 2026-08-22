# RealityNG Data Retention Matrix

All periods below are recommendations, not approved legal periods. Every duration **REQUIRES PROFESSIONAL REVIEW**.

| Data class | Purpose / owner | Storage and access | Recommended disposition | Exception |
|---|---|---|---|---|
| Accounts | Authentication; RealityNG | PostgreSQL; user/support/admin | Active life + limited closure period; deactivate then minimize/anonymize | Security, dispute, law |
| Profiles | Marketplace identity; user | PostgreSQL/media; user and authorized operations | Delete/anonymize after verified request where permitted | Open workflow/fraud |
| Properties and public media | Marketplace; lister | PostgreSQL/object media; public approved fields, owner/admin writes | Archive after delisting; delete media when no exception | Dispute/audit |
| Providers/services | Marketplace; provider | PostgreSQL/media; public approved fields, provider/admin | Archive after closure; minimize public data | Complaint/contract |
| Verification documents | Trust review; submitter/RealityNG | Private object storage; subject and authorized reviewers | Shortest approved review/appeal period, then secure deletion | Fraud/legal hold |
| Inspection documents | Inspection evidence; inspector/customer | Private storage; participants/admin | Contract/report period then delete or archive | Claim/dispute |
| Construction documents | Project evidence; project parties | Private storage; stakeholders/admin | Project life + approved claims period | Claim/legal hold |
| Messages | Communication; participants | PostgreSQL; participants/admin under controlled need | Limited account/workflow period; anonymize where feasible | Harassment/dispute |
| Notifications | Delivery/status; recipient | PostgreSQL | Short operational period, then delete | Security notice |
| Transactions | Workflow ledger; parties | PostgreSQL; parties/authorized operations | Approved financial/contract period | Dispute/legal duty |
| Escrow records | Partner-event record; provider/parties | PostgreSQL/private proof storage | Approved financial/contract period | Reconciliation/dispute |
| Financing records | Application workflow; applicant/partner | PostgreSQL | Approved application/contract period | Complaint/regulatory request |
| Financing documents | Partner assessment; applicant | Private bucket; applicant and authorized reviewers | Delete rejected/abandoned files on approved schedule | Fraud/legal hold |
| Consent records | Proof of choice; data subject/RealityNG | PostgreSQL; subject support/admin | Retain version proof for defensible approved period | Claim/audit |
| Complaints/moderation | Safety and redress; parties/RealityNG | PostgreSQL/private evidence | Case life + approved appeals period | Recurrence/fraud |
| Audit logs | Security/integrity; RealityNG | PostgreSQL/log platform; restricted operations | Tamper-resistant approved security period | Incident/legal hold |
| Backups | Recovery; RealityNG | Encrypted backup storage; infrastructure operators | Rolling expiry; deletion propagates on rotation | Recovery/legal hold |
| Operational logs | Reliability/security; RealityNG | Logging platform; restricted operators | Shortest useful operational window | Active incident |

Deletion requests require identity verification, scoped search, documented exceptions, downstream/provider notification where applicable, and closure evidence. The application has deletion guidance but no complete automated erasure workflow: **REQUIRES PROFESSIONAL REVIEW** and implementation before broad launch.

