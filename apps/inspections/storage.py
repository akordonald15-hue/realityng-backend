from __future__ import annotations

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage


class WalkthroughStorage(S3Boto3Storage):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("bucket_name", settings.WALKTHROUGH_STORAGE_BUCKET)
        kwargs.setdefault("default_acl", None)
        kwargs.setdefault("file_overwrite", False)
        kwargs.setdefault("querystring_auth", False)
        kwargs.setdefault("custom_domain", False)
        super().__init__(*args, **kwargs)


class PrivateInspectionStorage(S3Boto3Storage):
    bucket_setting_name = ""
    expiry_setting_name = "INSPECTION_SIGNED_URL_EXPIRY_SECONDS"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("bucket_name", getattr(settings, self.bucket_setting_name))
        kwargs.setdefault("default_acl", "private")
        kwargs.setdefault("file_overwrite", False)
        kwargs.setdefault("querystring_auth", True)
        kwargs.setdefault("querystring_expire", settings.INSPECTION_SIGNED_URL_EXPIRY_SECONDS)
        kwargs.setdefault("custom_domain", False)
        super().__init__(*args, **kwargs)


class PrivateInspectionEvidenceStorage(PrivateInspectionStorage):
    bucket_setting_name = "INSPECTION_EVIDENCE_BUCKET"


class PrivateInspectionReportStorage(PrivateInspectionStorage):
    bucket_setting_name = "INSPECTION_REPORT_BUCKET"


def get_walkthrough_storage():
    if getattr(settings, "USE_S3_MEDIA_STORAGE", False):
        return WalkthroughStorage()
    return FileSystemStorage(location=str(settings.BASE_DIR / "media" / "walkthroughs"))


def get_inspection_evidence_storage():
    if getattr(settings, "USE_S3_MEDIA_STORAGE", False):
        return PrivateInspectionEvidenceStorage()
    return FileSystemStorage(location=str(settings.BASE_DIR / "media" / "inspection-evidence"))


def get_inspection_report_storage():
    if getattr(settings, "USE_S3_MEDIA_STORAGE", False):
        return PrivateInspectionReportStorage()
    return FileSystemStorage(location=str(settings.BASE_DIR / "media" / "inspection-reports"))
