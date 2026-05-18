from __future__ import annotations

import copy

from backend.app.integrity.audit_signer import sign_audit_record, verify_signed_audit_record
from backend.app.integrity.canonical_json import canonical_sha256


def _audit_record() -> dict:
    return {
        "request_id": "req-1",
        "timestamp_utc": "2026-05-18T10:30:00Z",
        "upstream_call": True,
        "input": {"action": "ALLOW", "reason_codes": ["SAFE_INPUT"]},
        "output": {"action": "ALLOW", "reason_codes": ["SAFE_OUTPUT"]},
        "validator": {
            "validator_result": "PASS",
            "output_action": "ALLOW",
            "reason_codes": ["SAFE_OUTPUT"],
        },
        "final_action": "ALLOW",
        "reason_codes": ["SAFE_INPUT"],
    }


def test_audit_record_signing_adds_integrity_fields() -> None:
    signed = sign_audit_record(_audit_record())

    assert signed["integrity"]["signature"]
    assert signed["integrity"]["hash_alg"] == "SHA-256"
    assert signed["integrity"]["signature_alg"] == "MOCK-ML-DSA"


def test_signed_audit_record_verifies_successfully() -> None:
    signed = sign_audit_record(_audit_record())

    assert verify_signed_audit_record(signed) is True


def test_tampered_final_action_fails_verification() -> None:
    signed = sign_audit_record(_audit_record())
    tampered = copy.deepcopy(signed)
    tampered["final_action"] = "BLOCK"

    assert verify_signed_audit_record(tampered) is False


def test_tampered_reason_codes_fail_verification() -> None:
    signed = sign_audit_record(_audit_record())
    tampered = copy.deepcopy(signed)
    tampered["validator"]["reason_codes"] = ["OUTPUT_SYSTEM_PROMPT_LEAK"]

    assert verify_signed_audit_record(tampered) is False


def test_signature_field_is_excluded_from_canonical_hash() -> None:
    signed = sign_audit_record(_audit_record())
    changed_signature = copy.deepcopy(signed)
    changed_signature["integrity"]["signature"] = "different-signature"

    assert canonical_sha256(signed) == canonical_sha256(changed_signature)
