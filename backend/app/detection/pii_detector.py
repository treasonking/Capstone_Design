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
        "PHONE_INTL",
        ReasonCode.PII_PHONE_DETECTED.value,
        re.compile(
            r"(?<![A-Za-z0-9])"
            r"(?:\+82|0082|\(\+82\))"
            r"[\s\-\.]*"
            r"(?:\(?0?1[016789]\)?|\(?10\)?)"
            r"[\s\-\.]*"
            r"\d{3,4}"
            r"[\s\-\.]*"
            r"\d{4}"
            r"(?!\d)"
        ),
        0.9,
    ),
    (
        "PHONE",
        ReasonCode.PII_PHONE_DETECTED.value,
        re.compile(
            r"(?<![A-Za-z0-9])(?:\+?82[-.\s]?)?0?1[016789][-\s.]?\d{3,4}[-\s.]?\d{4}(?!\d)"
        ),
        0.9,
    ),
    (
        "ADDRESS",
        ReasonCode.PII_ADDRESS_DETECTED.value,
        re.compile(
            r"(?<![A-Za-z0-9])"
            r"(?:(?:서울|부산|대구|인천|광주|대전|울산|세종)"
            r"(?:특별시|광역시|특별자치시)?|"
            r"[가-힣]+(?:도|특별자치도))?\s*"
            r"(?:[가-힣]+시\s+)?"
            r"[가-힣]+(?:시|군|구)\s+"
            r"[가-힣0-9]+(?:읍|면|동|가|로|길)\s+"
            r"\d+(?:-\d+)?(?:번지)?"
            r"(?!\d)"
        ),
        0.88,
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
        re.compile(r"(?<!\d)(?!01[016789][-.\s]?)\d{2,6}[-\s]\d{2,6}[-\s]\d{2,7}(?!\d)"),
        0.75,
    ),
]

_ACCOUNT_CONTEXT_TERMS = (
    "계좌",
    "계좌번호",
    "입금",
    "송금",
    "예금주",
    "은행",
    "국민은행",
    "신한은행",
    "우리은행",
    "하나은행",
    "농협",
    "카카오뱅크",
    "토스뱅크",
    "케이뱅크",
    "ibk",
    "기업은행",
    "환불",
    "환급",
    "가상계좌",
    "가상 계좌",
)
_NON_ACCOUNT_CONTEXT_TERMS = (
    "승인번호",
    "승인 번호",
    "주문번호",
    "주문 번호",
    "결제번호",
    "거래번호",
    "접수번호",
    "예약번호",
    "상품코드",
    "인증번호",
    "쿠폰번호",
    "문서번호",
    "문서 코드",
    "티켓 번호",
    "티켓번호",
    "송장번호",
)
_MATH_CONTEXT_TERMS = ("계산", "수식", "예제", "더하기", "빼기", "곱하기", "나누기")
_PHONE_EXCLUSION_CONTEXT_TERMS = (
    "버전",
    "version",
    "release",
    "rfc",
    "section",
    "country",
    "area",
    "explanation",
    "장비번호",
    "장비 번호",
)
_ADDRESS_CONTEXT_TERMS = (
    "주소",
    "소재지",
    "거주지",
    "배송지",
    "주민등록",
    "전입",
    "행정복지센터",
    "주민센터",
    "동사무소",
    "민원",
)
_ADDRESS_EXCLUSION_CONTEXT_TERMS = (
    "지역 설명",
    "예시 지역",
    "행정구역",
    "관할",
    "일대",
    "부근",
    "근처",
    "방향",
    "위치 설명",
    "지도",
)
_ADDRESS_TOKEN_SUFFIXES = ("로", "길", "동", "가", "읍", "면")


def _overlaps(existing: list[DetectionResult], start: int, end: int) -> bool:
    for item in existing:
        if not (end <= item.start or start >= item.end):
            return True
    return False


def _context(text: str, start: int, end: int, window: int = 24) -> str:
    return text[max(0, start - window) : min(len(text), end + window)].lower()


def _has_any(context: str, terms: tuple[str, ...]) -> bool:
    return any(term.lower() in context for term in terms)


def _looks_like_math_expression(candidate: str, context: str) -> bool:
    if _has_any(context, _MATH_CONTEXT_TERMS):
        return True
    groups = re.split(r"[-\s]+", candidate)
    return len(groups) >= 3 and groups[-1] in {"90", "00"} and not _has_any(context, _ACCOUNT_CONTEXT_TERMS)


def _looks_like_non_account_identifier(context: str) -> bool:
    return _has_any(context, _NON_ACCOUNT_CONTEXT_TERMS)


def _valid_account_candidate(raw: str, context: str) -> bool:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not 10 <= len(digits) <= 14:
        return False
    if "." in raw and not _has_any(context, _ACCOUNT_CONTEXT_TERMS):
        return False
    if _looks_like_non_account_identifier(context):
        return False
    if _looks_like_math_expression(raw, context):
        return False

    groups = re.split(r"[-\s]+", raw)
    has_account_context = _has_any(context, _ACCOUNT_CONTEXT_TERMS)
    bank_like_shape = (
        len(groups) == 3
        and 2 <= len(groups[0]) <= 6
        and 2 <= len(groups[1]) <= 6
        and 5 <= len(groups[2]) <= 7
    )
    return has_account_context or bank_like_shape


def _valid_phone_candidate(context: str) -> bool:
    return not _has_any(context, _PHONE_EXCLUSION_CONTEXT_TERMS)


def _valid_address_candidate(raw: str, context: str) -> bool:
    normalized = re.sub(r"\s+", " ", raw).strip()
    parts = normalized.split(" ")
    if len(parts) < 3:
        return False
    if not any(char.isdigit() for char in normalized):
        return False
    if _has_any(context, _ADDRESS_EXCLUSION_CONTEXT_TERMS):
        return False

    tail = parts[-2] if len(parts) >= 2 else ""
    has_detail_suffix = any(tail.endswith(suffix) for suffix in _ADDRESS_TOKEN_SUFFIXES)
    has_lot_number = bool(re.search(r"\d+(?:-\d+)?(?:번지)?$", parts[-1]))
    has_address_context = _has_any(context, _ADDRESS_CONTEXT_TERMS)
    return has_detail_suffix and has_lot_number and (has_address_context or len(parts) >= 4)


def detect_pii(text: str) -> list[DetectionResult]:
    """Detect common PII patterns with deterministic regex rules."""
    if not text:
        return []

    results: list[DetectionResult] = []
    for category, reason_code, pattern, score in _PII_PATTERNS:
        for match in pattern.finditer(text):
            matched_text = match.group(0)

            match_context = _context(text, match.start(), match.end())
            if category.startswith("PHONE"):
                if _overlaps(results, match.start(), match.end()):
                    continue
                if not _valid_phone_candidate(match_context):
                    continue

            if category == "ADDRESS":
                if _overlaps(results, match.start(), match.end()):
                    continue
                if not _valid_address_candidate(matched_text, match_context):
                    continue

            if category == "ACCOUNT":
                if _overlaps(results, match.start(), match.end()):
                    continue
                if not _valid_account_candidate(matched_text, match_context):
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
