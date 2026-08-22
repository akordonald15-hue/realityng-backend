# RealityNG Sprint 15 Private Data Audit

Status: technically complete; operational follow-ups recorded  
Date: 2026-08-21

## Storage Classification and Runtime Evidence

| File class | Bucket | Policy | Signed expiry | API authorization |
| --- | --- | --- | --- | --- |
| Verification documents | `realityng-verification-private` | Private | 300 seconds | Owner request/admin only |
| Inspection evidence | `realityng-inspection-evidence` | Private | 300 seconds | Evidence visibility plus inspection relationship/admin |
| Inspection reports | `realityng-inspection-reports` | Private | 300 seconds | Requester/property owner/current inspector/admin |
| Construction evidence | `realityng-construction-evidence` | Private | 300 seconds | Project authorization and evidence visibility/admin |
| Payment proofs | `realityng-payment-proof-private` | Private | 300 seconds | Transaction participant/authorized manager/admin |
| Financing documents | `realityng-financing-documents-private` | Private | 300 seconds | Applicant/admin; property ownership alone is insufficient |

MinIO created every bucket successfully. `mc anonymous get` reported `private`
for every sensitive bucket. Each Django storage backend completed a signed
read probe against MinIO. Storage classes force private ACLs, signed query
authentication, short expiry, disabled overwrite, and no custom domain.

## API and Serialization Results

- Authorized signed access: PASS for every private file domain through existing
  and Sprint 15 regression coverage.
- Unrelated-user access: DENIED.
- Property owner access to applicant financing documents: DENIED.
- Inactive inspection assignment access: DENIED after Sprint 15 fix.
- Raw payment-proof and financing file fields: absent from normal serializers.
- Inspection/construction serializers return signed URLs only after object-level
  authorization.
- Verification URLs are generated only inside an owner/admin-scoped parent
  response.
- Signed responses use `Cache-Control: no-store, private` on explicit endpoints.

## Upload Security

MIME allowlists, extension allowlists, maximum sizes, and real-content checks
exist for verification, inspection, construction, payment, and financing
uploads. PDFs require the PDF magic header; images are decoded and verified;
supported video types receive container-header checks. Empty and malformed
files fail content verification. Display filenames are sanitized for
verification/payment/financing documents, and storage rejects traversal paths.
Object keys are relationship-scoped and private storage disables overwrite.

Malware scanning and asynchronous quarantine are not implemented. This is a
recorded future defense-in-depth control; it is not represented as existing.

