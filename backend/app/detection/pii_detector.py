from __future__ import annotations

import re

from .models import DetectionResult, DetectorType
from .reason_codes import ReasonCode


_PII_PATTERNS: list[tuple[str, str, re.Pattern[str], float]] = [
    (
        "EMAIL",
        ReasonCode.PII_EMAIL_DETECTED.value,
        re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}\b",
            flags=re.IGNORECASE,
        ),
        0.95,
    ),
    (
        "PHONE",
        ReasonCode.PII_PHONE_DETECTED.value,
        re.compile(
            r"(?<!\d)(?:\+?82[-.\s]?)?0?1[016789][-\s.]?\d{3,4}[-\s.]?\d{4}(?!\d)"
        ),
        0.9,
    ),
    (
        "RRN",
        ReasonCode.PII_RRN_DETECTED.value,
        re.compile(r"(?<!\d)\d{6}[-\s]?[1-4]\d{6}(?!\d)"),
        0.98,
    ),
    (
        "ACCOUNT",
        ReasonCode.PII_ACCOUNT_DETECTED.value,
        re.compile(r"(?<!\d)(?!01[016789][-.\s]?)\d{2,4}[-\s]\d{2,6}[-\s]\d{2,6}(?!\d)"),
        0.7,
    ),
]


def _overlaps(existing: list[DetectionResult], start: int, end: int) -> bool:
    for item in existing:
        if not (end <= item.start or start >= item.end):
            return True
    return False


def _valid_account_candidate(raw: str) -> bool:
    digits = "".join(ch for ch in raw if ch.isdigit())
    return 10 <= len(digits) <= 14


def detect_pii(text: str) -> list[DetectionResult]:
    """Detect common PII patterns with deterministic regex rules."""
    if not text:
        return []

    results: list[DetectionResult] = []
    for category, reason_code, pattern, score in _PII_PATTERNS:
        for match in pattern.finditer(text):
            matched_text = match.group(0)

            if category == "ACCOUNT":
                if _overlaps(results, match.start(), match.end()):
                    continue
                if not _valid_account_candidate(matched_text):
                    continue

            results.append(
                DetectionResult(
                    detector_type=DetectorType.PII,
                    category=category,
                    reason_code=reason_code,
                    start=match.start(),
                    end=match.end(),
                    matched_text=matched_text,
                    score=score,
                )
            )
    return sorted(results, key=lambda item: (item.start, item.end))
