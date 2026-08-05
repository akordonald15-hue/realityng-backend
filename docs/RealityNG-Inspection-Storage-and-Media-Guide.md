# RealityNG Inspection Storage and Media Guide

## Buckets

| Data | Default Bucket | Public? | Notes |
| --- | --- | --- | --- |
| Walkthrough videos | `WALKTHROUGH_STORAGE_BUCKET` | Public after approval | Uses the public media pattern; moderation controls visibility. |
| Inspection evidence | `INSPECTION_EVIDENCE_BUCKET` | Private | Access through backend-authorized signed URLs only. |
| Inspection reports | `INSPECTION_REPORT_BUCKET` | Private | Report document access is signed and private. |

## Environment Variables

- `WALKTHROUGH_MAX_FILE_SIZE_MB`
- `WALKTHROUGH_MAX_VIDEOS_PER_PROPERTY`
- `WALKTHROUGH_ALLOWED_MIME_TYPES`
- `WALKTHROUGH_ALLOWED_EXTENSIONS`
- `WALKTHROUGH_STORAGE_BUCKET`
- `WALKTHROUGH_UPLOAD_URL_EXPIRY_SECONDS`
- `WALKTHROUGH_PUBLIC_BASE_URL`
- `WALKTHROUGH_REQUIRE_MODERATION`
- `INSPECTION_EVIDENCE_BUCKET`
- `INSPECTION_REPORT_BUCKET`
- `INSPECTION_SIGNED_URL_EXPIRY_SECONDS`
- `INSPECTION_MAX_EVIDENCE_FILE_SIZE_MB`
- `INSPECTION_MAX_REPORT_FILE_SIZE_MB`
- `INSPECTION_EVIDENCE_ALLOWED_MIME_TYPES`
- `INSPECTION_EVIDENCE_ALLOWED_EXTENSIONS`
- `INSPECTION_REPORT_ALLOWED_MIME_TYPES`
- `INSPECTION_REPORT_ALLOWED_EXTENSIONS`

## Shared VPS Constraints

- Do not run heavy video transcoding on the RealityNG/Caretekk shared production VPS.
- Do not run destructive or high-concurrency media load tests on production.
- Validate storage with synthetic files only.
- Keep private evidence cache headers as `no-store, private`.

## Rollback Notes

- Walkthrough and evidence files should not be deleted during a code rollback.
- Database rollback must account for Sprint 10 inspection migrations.
- Private bucket policies should remain unchanged unless explicitly approved.
