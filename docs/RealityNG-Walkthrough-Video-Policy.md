# RealityNG Walkthrough Video Policy

## Purpose

Walkthrough videos help buyers and renters understand a property before requesting a viewing, applying, or sending money. They are evidence-supporting media, not a substitute for legal verification, physical inspection, or due diligence.

## Who Can Upload

Approved product policy allows:

- landlords;
- agents;
- verified property managers;
- admins.

Current backend enforcement is conservative because the property model does not yet store assigned agent or property-manager relationships. In Sprint 10, uploads are allowed for:

- admins;
- owners of the property who hold an approved landlord or agent role.

Future work should add an explicit managed-property relationship before enabling non-owner verified property managers.

## Moderation

- New walkthroughs start as `draft`.
- Uploaders submit videos for review.
- Only admins can approve, reject, hide, or restore walkthroughs.
- Public property pages show only `approved` walkthroughs.
- Rejected, hidden, archived, failed, and pending videos are not public.

## Upload Security

- Allowed MIME types: configured by `WALKTHROUGH_ALLOWED_MIME_TYPES`.
- Allowed extensions: configured by `WALKTHROUGH_ALLOWED_EXTENSIONS`.
- Default max size: `WALKTHROUGH_MAX_FILE_SIZE_MB`.
- Default max videos per property: `WALKTHROUGH_MAX_VIDEOS_PER_PROPERTY`.
- HTML is rejected in titles and descriptions.
- Public serializers do not expose storage credentials.

## Product Limitations

- No heavy video transcoding is performed on the shared VPS.
- No automatic AI content moderation is included.
- No production CDN/video pipeline is required for Sprint 10.
- Videos are public media after approval, unlike private inspection evidence.
