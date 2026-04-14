from __future__ import annotations

import re

from .models import DetectionResult, DetectorType
from .reason_codes import ReasonCode


_PII_PATTERNS: list[tuple[str, str, re.Pattern[str], float]] = [
    (
        "EMAIL",
        ReasonCode.PII_EMAIL_DETECTED.value,
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        0.95,
    ),
    (
        "PHONE",
        ReasonCode.PII_PHONE_DETECTED.value,
        re.compile(r"\b01[016789]-?\d{3,4}-?\d{4}\b"),
        0.9,
    ),
    (
        "RRN",
        ReasonCode.PII_RRN_DETECTED.value,
        re.compile(r"\b\d{6}-?[1-4]\d{6}\b"),
        0.98,
    ),
    (
        "ACCOUNT",
        ReasonCode.PII_ACCOUNT_DETECTED.value,
        re.compile(r"\b(?!01[016789]-)\d{2,4}-\d{2,6}-\d{2,6}\b"),
        0.7,
    ),
]


def detect_pii(text: str) -> list[DetectionResult]:
    """Detect common PII patterns with deterministic regex rules."""
    if not text:
        return []

    results: list[DetectionResult] = []
    for category, reason_code, pattern, score in _PII_PATTERNS:
        for match in pattern.finditer(text):
            results.append(
                DetectionResult(
                    detector_type=DetectorType.PII,
                    category=category,
                    reason_code=reason_code,
                    start=match.start(),
                    end=match.end(),
                    matched_text=match.group(0),
                    score=score,
                )
            )
    return sorted(results, key=lambda item: (item.start, item.end))
