from __future__ import annotations

from backend.app.detection.models import DetectionResult
from backend.app.detection.reason_codes import ReasonCode


def _mask_email(value: str) -> str:
    local, sep, domain = value.partition("@")
    if not sep:
        return "*" * len(value)
    keep = local[:2] if len(local) >= 2 else local[:1]
    return f"{keep}{'*' * max(len(local) - len(keep), 3)}@{domain}"


def _mask_phone(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if digits.startswith("82") and len(digits) >= 11:
        digits = "0" + digits[2:]
    if len(digits) < 10:
        return "*" * len(value)
    if len(digits) == 10:
        # 10-digit local formats
        return f"{digits[:3]}-{digits[3:5]}**-****"
    return f"{digits[:3]}-{digits[3:5]}**-****"


def _mask_rrn(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) != 13:
        return "*" * len(value)
    return f"{digits[:6]}-{digits[6]}******"


def _mask_account(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) < 6:
        return "*" * len(value)
    return f"{digits[:2]}{'*' * max(len(digits) - 4, 6)}{digits[-2:]}"


def _mask_by_reason(reason_code: str, value: str) -> str:
    if reason_code == ReasonCode.PII_EMAIL_DETECTED.value:
        return _mask_email(value)
    if reason_code == ReasonCode.PII_PHONE_DETECTED.value:
        return _mask_phone(value)
    if reason_code == ReasonCode.PII_RRN_DETECTED.value:
        return _mask_rrn(value)
    if reason_code == ReasonCode.PII_ACCOUNT_DETECTED.value:
        return _mask_account(value)
    return value


def apply_masking(text: str, detections: list[DetectionResult]) -> str:
    """Apply partial masking for PII detections while preserving text layout."""
    if not detections:
        return text

    masked = text
    # Reverse order keeps earlier indexes stable after each replacement.
    for detection in sorted(detections, key=lambda item: item.start, reverse=True):
        original = masked[detection.start : detection.end]
        replacement = _mask_by_reason(detection.reason_code, original)
        masked = masked[: detection.start] + replacement + masked[detection.end :]
    return masked
