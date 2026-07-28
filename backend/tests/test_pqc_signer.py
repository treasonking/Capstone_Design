from __future__ import annotations

from backend.app.integrity.pqc_signer import MockAuditSigner, MockMLDSASigner


def test_mock_mldsa_signer_signs_and_verifies_digest() -> None:
    signer = MockAuditSigner(secret_key=b"unit-test-key")
    digest = b"0" * 32

    signature = signer.sign(digest)

    assert signer.hash_alg == "SHA-256"
    assert signer.signature_alg == "HMAC-SHA256-MOCK"
    assert signature
    assert signer.verify(digest, signature) is True


def test_mock_mldsa_signer_rejects_modified_digest() -> None:
    signer = MockAuditSigner(secret_key=b"unit-test-key")
    signature = signer.sign(b"0" * 32)

    assert signer.verify(b"1" * 32, signature) is False


def test_legacy_mock_mldsa_import_is_hmac_alias() -> None:
    signer = MockMLDSASigner(secret_key=b"unit-test-key")

    assert isinstance(signer, MockAuditSigner)
    assert signer.signature_alg == "HMAC-SHA256-MOCK"
