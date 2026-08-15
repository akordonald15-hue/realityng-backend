"""Reusable validation for payment proof uploads.

Mirrors apps/trust/validators.py's real-content-verification approach
(extension + declared content type + size + actual file content, not
just trusting metadata), applied to payment proof evidence (receipts,
transfer confirmations, screenshots) instead of verification documents.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

PDF_MAGIC_BYTES = b"%PDF-"


def validate_payment_proof(value) -> None:
    """Validate an uploaded payment proof file.

    Checks, in order: declared content type, file extension, file size,
    and actual file content (real magic-byte/structure verification,
    not just the declared MIME type or extension).

    Raises django.core.exceptions.ValidationError on any failure, so this
    can be used directly as a model/form field validator or called
    explicitly from a DRF serializer's validate_<field> method.
    """
    content_type = getattr(value, "content_type", "")
    allowed_types = set(settings.PAYMENT_PROOF_ALLOWED_TYPES)
    if content_type not in allowed_types:
        raise ValidationError(
            f"Unsupported file type '{content_type}'. Allowed types: "
            f"{', '.join(sorted(allowed_types))}."
        )

    allowed_extensions = set(settings.PAYMENT_PROOF_ALLOWED_EXTENSIONS)
    extension = Path(value.name).suffix.lower()
    if extension not in allowed_extensions:
        raise ValidationError(
            f"File extension must be one of: {', '.join(sorted(allowed_extensions))}."
        )

    max_size = settings.PAYMENT_PROOF_MAX_SIZE_MB * 1024 * 1024
    if value.size > max_size:
        raise ValidationError(
            f"File must be {settings.PAYMENT_PROOF_MAX_SIZE_MB}MB or smaller."
        )

    _verify_real_content(value, content_type)
    value.seek(0)


def _verify_real_content(value, content_type: str) -> None:
    """Confirm the file's actual bytes match its declared type.

    A renamed executable with a spoofed Content-Type header will fail
    here even though it passed the extension/MIME allowlist checks above.
    """
    if content_type == "application/pdf":
        header = value.read(len(PDF_MAGIC_BYTES))
        value.seek(0)
        if header != PDF_MAGIC_BYTES:
            raise ValidationError("Uploaded file must be a valid PDF.")
        return

    if content_type in {"image/jpeg", "image/png"}:
        try:
            image = Image.open(value)
            image.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise ValidationError("Uploaded file must be a valid image.") from exc
        finally:
            value.seek(0)
        return

    # Should be unreachable given the allowlist check above, but fail
    # closed rather than silently accepting an unverified file type.
    raise ValidationError("Unable to verify file content for this type.")


def compute_checksum(value) -> str:
    """Compute a SHA-256 checksum of the file content for dedup/audit use."""
    hasher = hashlib.sha256()
    for chunk in value.chunks():
        hasher.update(chunk)
    value.seek(0)
    return hasher.hexdigest()


def sanitize_original_filename(filename: str) -> str:
    """Strip path components and unsafe characters from a display filename.

    The actual storage path is generated independently (see
    PaymentProof.file's upload_to); this only sanitizes the
    human-readable original_filename kept for display purposes, so it
    can never be used to construct a filesystem path.
    """
    name = Path(filename).name  # strips any directory components
    safe_chars = "-_. "
    cleaned = "".join(c for c in name if c.isalnum() or c in safe_chars)
    return cleaned.strip() or "document"


def validate_financing_document(value) -> None:
    content_type = getattr(value, "content_type", "")
    allowed_types = set(settings.FINANCING_DOCUMENT_ALLOWED_TYPES)
    if content_type not in allowed_types:
        raise ValidationError(
            f"Unsupported file type '{content_type}'. Allowed types: "
            f"{', '.join(sorted(allowed_types))}."
        )

    allowed_extensions = set(settings.FINANCING_DOCUMENT_ALLOWED_EXTENSIONS)
    extension = Path(value.name).suffix.lower()
    if extension not in allowed_extensions:
        raise ValidationError(
            f"File extension must be one of: {', '.join(sorted(allowed_extensions))}."
        )

    max_size = settings.FINANCING_DOCUMENT_MAX_SIZE_MB * 1024 * 1024
    if value.size > max_size:
        raise ValidationError(
            f"File must be {settings.FINANCING_DOCUMENT_MAX_SIZE_MB}MB or smaller."
        )

    _verify_financing_document_content(value, content_type)
    value.seek(0)


def _verify_financing_document_content(value, content_type: str) -> None:
    if content_type == "application/pdf":
        header = value.read(len(PDF_MAGIC_BYTES))
        value.seek(0)
        if header != PDF_MAGIC_BYTES:
            raise ValidationError("Uploaded file must be a valid PDF.")
        return

    if content_type in {"image/jpeg", "image/png"}:
        _verify_real_content(value, content_type)
        return

    raise ValidationError("Unable to verify file content for this type.")
