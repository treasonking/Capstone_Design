from __future__ import annotations

import re

from .models import DetectionResult, DetectorType
from .reason_codes import ReasonCode


_INJECTION_PATTERNS: list[tuple[str, str, re.Pattern[str], float]] = [
    (
        "IGNORE_PREVIOUS_INSTRUCTIONS",
        ReasonCode.INJ_IGNORE_PREVIOUS_INSTRUCTIONS.value,
        re.compile(
            r"(이전\s*(지시|지침)(를)?\s*무시|이전\s*(규칙|설정)\s*무시|"
            r"ignore\s+(all\s+)?previous\s+instructions?|"
            r"do\s+not\s+follow\s+previous\s+instructions?)",
            flags=re.IGNORECASE,
        ),
        0.95,
    ),
    (
        "REVEAL_SYSTEM_PROMPT",
        ReasonCode.INJ_REVEAL_SYSTEM_PROMPT.value,
        re.compile(
            r"(시스템\s*(프롬프트|지시문)(를)?\s*(보여줘|공개|출력)|"
            r"system\s*(prompt|instruction)(를)?\s*(보여줘|출력)|"
            r"reveal\s+(the\s+)?system\s+(prompt|instruction)|"
            r"print\s+(the\s+)?hidden\s+prompt)",
            flags=re.IGNORECASE,
        ),
        0.98,
    ),
    (
        "POLICY_BYPASS_ATTEMPT",
        ReasonCode.INJ_POLICY_BYPASS_ATTEMPT.value,
        re.compile(
            r"(정책(을)?\s*우회|내부\s*규칙(을)?\s*알려줘|bypass\s+policy|"
            r"ignore\s+safety\s+rules?|"
            r"jailbreak|developer\s+mode|act\s+as\s+an?\s+unrestricted\s+assistant|"
            r"보안\s*(정책|규칙)\s*(끄고|해제))",
            flags=re.IGNORECASE,
        ),
        0.92,
    ),
]


def detect_injection(text: str) -> list[DetectionResult]:
    """Detect prompt injection attempts with transparent rule patterns."""
    if not text:
        return []

    results: list[DetectionResult] = []
    for category, reason_code, pattern, score in _INJECTION_PATTERNS:
        for match in pattern.finditer(text):
            results.append(
                DetectionResult(
                    detector_type=DetectorType.INJECTION,
                    category=category,
                    reason_code=reason_code,
                    start=match.start(),
                    end=match.end(),
                    matched_text=match.group(0),
                    score=score,
                )
            )
    return sorted(results, key=lambda item: (item.start, item.end))
