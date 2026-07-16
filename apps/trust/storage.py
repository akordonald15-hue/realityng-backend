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

    Settings are read in __init__, not as class attributes, since class
    attributes are evaluated at class-definition time -- which happens
    during Django's app-loading sequence, before settings are guaranteed
    to be fully configured. Reading them in __init__ defers evaluation
    until the storage is actually instantiated (lazily, via
    get_verification_storage() below), which only ever happens after
    Django has finished booting.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("bucket_name", settings.MINIO_PRIVATE_BUCKET_NAME)
        kwargs.setdefault("default_acl", "private")
        kwargs.setdefault("file_overwrite", False)
        kwargs.setdefault("querystring_auth", True)
        kwargs.setdefault("querystring_expire", 300)
        kwargs.setdefault("custom_domain", False)
        super().__init__(*args, **kwargs)


def get_verification_storage():
    """Resolve the correct storage backend at access time, not at import time.

    Falls back to local filesystem storage when USE_S3_MEDIA_STORAGE is
    False (local dev, tests), and uses the real private bucket in
    production. Using a callable here -- Django's supported pattern for
    deferred storage resolution -- means this only ever runs when a
    FileField actually needs its storage, long after Django has fully
    booted and settings are guaranteed to be available.
    """
    from django.core.files.storage import FileSystemStorage

    if getattr(settings, "USE_S3_MEDIA_STORAGE", False):
        return PrivateVerificationDocumentStorage()
    return FileSystemStorage(
        location=str(settings.BASE_DIR / "media" / "verification-private")
    )
