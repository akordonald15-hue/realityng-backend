"""Tests for upload validation: extension, size, MIME, and real content."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from apps.trust.validators import (
    compute_checksum,
    sanitize_original_filename,
    validate_verification_document,
)

pytestmark = pytest.mark.django_db


class TestValidateVerificationDocument:
    def test_valid_pdf_passes(self, valid_pdf_file):
        validate_verification_document(valid_pdf_file)  # should not raise

    def test_forged_mime_type_rejected(self, invalid_pdf_file):
        # Extension and declared content_type both claim PDF, but the
        # actual bytes are not a real PDF -- must fail on real-content check.
        with pytest.raises(ValidationError):
            validate_verification_document(invalid_pdf_file)

    def test_disallowed_extension_rejected(self, disallowed_extension_file):
        with pytest.raises(ValidationError):
            validate_verification_document(disallowed_extension_file)

    def test_oversized_file_rejected(self, oversized_file):
        with pytest.raises(ValidationError):
            validate_verification_document(oversized_file)


class TestComputeChecksum:
    def test_checksum_is_deterministic(self, valid_pdf_file):
        checksum_a = compute_checksum(valid_pdf_file)
        valid_pdf_file.seek(0)
        checksum_b = compute_checksum(valid_pdf_file)
        assert checksum_a == checksum_b

    def test_checksum_differs_for_different_content(self, valid_pdf_file, invalid_pdf_file):
        checksum_a = compute_checksum(valid_pdf_file)
        checksum_b = compute_checksum(invalid_pdf_file)
        assert checksum_a != checksum_b


class TestSanitizeOriginalFilename:
    def test_strips_path_components(self):
        assert sanitize_original_filename("../../etc/passwd") == "passwd"

    def test_strips_unsafe_characters(self):
        result = sanitize_original_filename("cac<script>.pdf")
        assert "<" not in result and ">" not in result

    def test_empty_result_falls_back_to_default(self):
        assert sanitize_original_filename("***") == "document"

    def test_preserves_safe_filename(self):
        assert sanitize_original_filename("CAC Certificate - 2026.pdf") == "CAC Certificate - 2026.pdf"
