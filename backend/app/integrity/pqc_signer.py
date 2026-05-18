from __future__ import annotations

import base64
import hmac
from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol


class AuditSigner(Protocol):
    hash_alg: str
    signature_alg: str
    public_key_id: str

    def sign(self, digest: bytes) -> str:
        ...

    def verify(self, digest: bytes, signature: str) -> bool:
        ...


@dataclass(slots=True)
class MockMLDSASigner:
    """PQC-compatible development signer, not a real ML-DSA implementation."""

    secret_key: bytes = b"capstone-design-dev-mock-mldsa-key"
    public_key_id: str = "mock-pqc-key-2026-01"
    hash_alg: str = "SHA-256"
    signature_alg: str = "MOCK-ML-DSA"

    def sign(self, digest: bytes) -> str:
        signature = hmac.new(self.secret_key, digest, sha256).digest()
        return base64.b64encode(signature).decode("ascii")

    def verify(self, digest: bytes, signature: str) -> bool:
        expected = self.sign(digest)
        return hmac.compare_digest(expected, signature)
