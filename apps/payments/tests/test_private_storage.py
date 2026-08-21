from apps.construction.storage import PrivateConstructionEvidenceStorage
from apps.inspections.storage import (
    PrivateInspectionEvidenceStorage,
    PrivateInspectionReportStorage,
)
from apps.payments.storage import (
    PrivateFinancingDocumentStorage,
    PrivatePaymentProofStorage,
)
from apps.trust.storage import PrivateVerificationDocumentStorage


def test_all_sensitive_storage_backends_are_private_signed_and_non_overwriting(settings):
    settings.VERIFICATION_SIGNED_URL_EXPIRY = 101
    settings.INSPECTION_SIGNED_URL_EXPIRY_SECONDS = 102
    settings.CONSTRUCTION_SIGNED_URL_EXPIRY_SECONDS = 103
    settings.PAYMENT_PROOF_SIGNED_URL_EXPIRY = 104
    settings.FINANCING_DOCUMENT_SIGNED_URL_EXPIRY = 105

    storages = [
        (PrivateVerificationDocumentStorage(), settings.VERIFICATION_DOCUMENT_BUCKET_NAME, 101),
        (PrivateInspectionEvidenceStorage(), settings.INSPECTION_EVIDENCE_BUCKET, 102),
        (PrivateInspectionReportStorage(), settings.INSPECTION_REPORT_BUCKET, 102),
        (PrivateConstructionEvidenceStorage(), settings.CONSTRUCTION_EVIDENCE_BUCKET, 103),
        (PrivatePaymentProofStorage(), settings.PAYMENT_PROOF_BUCKET_NAME, 104),
        (PrivateFinancingDocumentStorage(), settings.FINANCING_DOCUMENT_BUCKET_NAME, 105),
    ]

    for storage, expected_bucket, expected_expiry in storages:
        assert storage.bucket_name == expected_bucket
        assert storage.default_acl == "private"
        assert storage.querystring_auth is True
        assert storage.querystring_expire == expected_expiry
        assert storage.file_overwrite is False
        assert storage.custom_domain is False


def test_financing_bucket_default_matches_local_infrastructure(settings):
    assert settings.FINANCING_DOCUMENT_BUCKET_NAME == "realityng-financing-documents-private"
