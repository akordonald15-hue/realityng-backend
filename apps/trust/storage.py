"""Private storage backend for verification documents.

Verification documents (CAC certificates, government IDs, ownership
evidence) must never be publicly accessible. This storage backend forces
private ACLs and signed, time-limited URLs regardless of the global
media storage configuration used for public assets like property images.
"""

from __future__ import annotations

from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class PrivateVerificationDocumentStorage(S3Boto3Storage):
    """S3/MinIO-backed storage for verification documents.

    Distinct bucket from public media, always private, always signed.
    """

    bucket_name = settings.MINIO_PRIVATE_BUCKET_NAME
    default_acl = "private"
    file_overwrite = False
    querystring_auth = True
    querystring_expire = 300  # signed URL validity, in seconds (5 minutes)
    custom_domain = False  # never serve through a public CDN-style domain
