from __future__ import annotations

import base64
import hmac
import os
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Protocol


class AuditSigner(Protocol):
    hash_alg: str
    signature_alg: str
    public_key_id: str
    implementation_status: str
    replacement_target: str | None

    def sign(self, digest: bytes) -> str:
        ...

    def verify(self, digest: bytes, signature: str) -> bool:
        ...


_DEVELOPMENT_HMAC_KEY = b"public-development-only-mock-integrity-key"


def _mock_hmac_key() -> bytes:
    configured = os.getenv("AUDIT_LOG_HMAC_KEY")
    return configured.encode("utf-8") if configured else _DEVELOPMENT_HMAC_KEY


@dataclass(slots=True)
class MockAuditSigner:
    """Development-only HMAC signer behind an ML-DSA-replaceable interface."""

    secret_key: bytes = field(default_factory=_mock_hmac_key)
    public_key_id: str = "mock-hmac-key-2026-01"
    hash_alg: str = "SHA-256"
    signature_alg: str = "HMAC-SHA256-MOCK"
    implementation_status: str = "MOCK_ONLY"
    replacement_target: str = "ML-DSA"

    def sign(self, digest: bytes) -> str:
        signature = hmac.new(self.secret_key, digest, sha256).digest()
        return base64.b64encode(signature).decode("ascii")

    def verify(self, digest: bytes, signature: str) -> bool:
        expected = self.sign(digest)
        return hmac.compare_digest(expected, signature)


# Backward-compatible import alias. This remains a mock HMAC implementation,
# not an ML-DSA algorithm.
MockMLDSASigner = MockAuditSigner
