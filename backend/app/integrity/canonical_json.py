from __future__ import annotations

import copy
import hashlib
import json
from typing import Any


def record_without_signature(record: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(record)
    integrity = normalized.get("integrity")
    if isinstance(integrity, dict):
        integrity.pop("signature", None)
    return normalized


def canonical_json_bytes(record: dict[str, Any]) -> bytes:
    return json.dumps(
        record_without_signature(record),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(record: dict[str, Any]) -> bytes:
    return hashlib.sha256(canonical_json_bytes(record)).digest()
