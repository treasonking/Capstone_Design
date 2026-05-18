from __future__ import annotations

import copy
from typing import Any

from backend.app.integrity.canonical_json import canonical_sha256
from backend.app.integrity.pqc_signer import AuditSigner, MockMLDSASigner


def _default_signer() -> MockMLDSASigner:
    return MockMLDSASigner()


def sign_audit_record(
    record: dict[str, Any],
    signer: AuditSigner | None = None,
) -> dict[str, Any]:
    active_signer = signer or _default_signer()
    signed_record = copy.deepcopy(record)
    signed_record["integrity"] = {
        "hash_alg": active_signer.hash_alg,
        "signature_alg": active_signer.signature_alg,
        "public_key_id": active_signer.public_key_id,
    }
    digest = canonical_sha256(signed_record)
    signed_record["integrity"]["signature"] = active_signer.sign(digest)
    return signed_record


def verify_signed_audit_record(
    record: dict[str, Any],
    signer: AuditSigner | None = None,
) -> bool:
    integrity = record.get("integrity")
    if not isinstance(integrity, dict):
        return False
    signature = integrity.get("signature")
    if not isinstance(signature, str) or not signature:
        return False

    active_signer = signer or _default_signer()
    if integrity.get("hash_alg") != active_signer.hash_alg:
        return False
    if integrity.get("signature_alg") != active_signer.signature_alg:
        return False
    if integrity.get("public_key_id") != active_signer.public_key_id:
        return False

    digest = canonical_sha256(record)
    return active_signer.verify(digest, signature)


def attach_integrity_failure(record: dict[str, Any], error: Exception) -> dict[str, Any]:
    failed_record = copy.deepcopy(record)
    failed_record["integrity"] = {
        "hash_alg": "SHA-256",
        "signature_alg": "UNSIGNED",
        "public_key_id": None,
        "signature": None,
        "status": "SIGNING_FAILED",
        "error": error.__class__.__name__,
    }
    return failed_record
