from __future__ import annotations

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage


class PrivateConstructionEvidenceStorage(S3Boto3Storage):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("bucket_name", settings.CONSTRUCTION_EVIDENCE_BUCKET)
        kwargs.setdefault("default_acl", "private")
        kwargs.setdefault("file_overwrite", False)
        kwargs.setdefault("querystring_auth", True)
        kwargs.setdefault("querystring_expire", settings.CONSTRUCTION_SIGNED_URL_EXPIRY_SECONDS)
        kwargs.setdefault("custom_domain", False)
        super().__init__(*args, **kwargs)


def get_construction_evidence_storage():
    if getattr(settings, "USE_S3_MEDIA_STORAGE", False):
        return PrivateConstructionEvidenceStorage()
    return FileSystemStorage(location=str(settings.BASE_DIR / "media" / "construction-evidence"))
