from __future__ import annotations

from backend.app.integrity.pqc_signer import MockMLDSASigner


def test_mock_mldsa_signer_signs_and_verifies_digest() -> None:
    signer = MockMLDSASigner()
    digest = b"0" * 32

    signature = signer.sign(digest)

    assert signer.hash_alg == "SHA-256"
    assert signer.signature_alg == "MOCK-ML-DSA"
    assert signature
    assert signer.verify(digest, signature) is True


def test_mock_mldsa_signer_rejects_modified_digest() -> None:
    signer = MockMLDSASigner()
    signature = signer.sign(b"0" * 32)

    assert signer.verify(b"1" * 32, signature) is False
