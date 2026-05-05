from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

from .models import DetectionResult
from .reason_codes import ReasonCode


@dataclass(frozen=True, slots=True)
class _PatternSpec:
    category: str
    label: str
    reason_code: str
    pattern: re.Pattern[str]
    confidence: float
    severity: str


_PII_PATTERNS: list[_PatternSpec] = [
    _PatternSpec(
        category="EMAIL",
        label="email",
        reason_code=ReasonCode.PII_EMAIL_DETECTED.value,
        pattern=re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}\b", flags=re.IGNORECASE),
        confidence=0.98,
        severity="MEDIUM",
    ),
    _PatternSpec(
        category="PHONE",
        label="phone",
        reason_code=ReasonCode.PII_PHONE_DETECTED.value,
        pattern=re.compile(
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
        confidence=0.95,
        severity="MEDIUM",
    ),
    _PatternSpec(
        category="PHONE",
        label="phone",
        reason_code=ReasonCode.PII_PHONE_DETECTED.value,
        pattern=re.compile(r"(?<![A-Za-z0-9])(?:\+?82[-.\s]?)?0?1[016789][-\s.]?\d{3,4}[-\s.]?\d{4}(?!\d)"),
        confidence=0.94,
        severity="MEDIUM",
    ),
    _PatternSpec(
        category="LANDLINE",
        label="phone",
        reason_code=ReasonCode.PII_LANDLINE_DETECTED.value,
        pattern=re.compile(r"(?<![A-Za-z0-9])0(?:2|[3-6][1-5])[-\s.]?\d{3,4}[-\s.]?\d{4}(?!\d)"),
        confidence=0.86,
        severity="LOW",
    ),
    _PatternSpec(
        category="ADDRESS",
        label="address",
        reason_code=ReasonCode.PII_ADDRESS_DETECTED.value,
        pattern=re.compile(
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
        confidence=0.88,
        severity="MEDIUM",
    ),
    _PatternSpec(
        category="RRN",
        label="resident_number",
        reason_code=ReasonCode.PII_RRN_DETECTED.value,
        pattern=re.compile(r"(?<!\d)\d{6}[-\s]?[1-4]\d{6}(?!\d)"),
        confidence=0.99,
        severity="CRITICAL",
    ),
    _PatternSpec(
        category="ACCOUNT",
        label="account",
        reason_code=ReasonCode.PII_ACCOUNT_DETECTED.value,
        pattern=re.compile(r"(?<!\d)(?!01[016789][-.\s]?)\d{2,6}[-\s]\d{2,6}[-\s]\d{2,7}(?!\d)"),
        confidence=0.76,
        severity="LOW",
    ),
    _PatternSpec(
        category="CARD",
        label="card",
        reason_code=ReasonCode.PII_CARD_DETECTED.value,
        pattern=re.compile(r"(?<!\d)(?:\d{4}[-\s]?){3}\d{4}(?!\d)"),
        confidence=0.84,
        severity="HIGH",
    ),
    _PatternSpec(
        category="IP",
        label="ip",
        reason_code=ReasonCode.PII_IP_DETECTED.value,
        pattern=re.compile(r"(?<!\d)(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?!\d)"),
        confidence=0.78,
        severity="LOW",
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
    "기업은행",
    "ibk",
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
    "송장번호",
    "ticket",
    "order",
    "version",
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
_CARD_CONTEXT_TERMS = (
    "카드",
    "신용카드",
    "체크카드",
    "카드번호",
    "결제",
    "승인",
    "payment",
    "visa",
    "mastercard",
)
_IP_CONTEXT_TERMS = ("ip", "아이피", "접속", "로그", "서버", "클라이언트", "client", "server")
_NAME_CONTEXT_PATTERNS = (
    re.compile(r"(?:민원인|담당자|고객|직원|성명|이름)\s*[:은는이가]?\s*([가-힣]{2,4})"),
    re.compile(r"\b([가-힣]{2,4})(?:님|씨|주무관|과장|팀장|선생님)\b"),
)
_NAME_EXCLUSIONS = {
    "행정복지",
    "주민센터",
    "보안정책",
    "시스템",
    "프롬프트",
    "규칙",
    "민원접수",
}
_ADDRESS_TOKEN_SUFFIXES = ("로", "길", "동", "가", "읍", "면")


def _context(text: str, start: int, end: int, window: int = 28) -> str:
    return text[max(0, start - window) : min(len(text), end + window)].lower()


def _has_any(context: str, terms: tuple[str, ...]) -> bool:
    return any(term.lower() in context for term in terms)


def _overlaps(existing: list[DetectionResult], start: int, end: int) -> bool:
    for item in existing:
        if item.start is None or item.end is None:
            continue
        if not (end <= item.start or start >= item.end):
            return True
    return False


def _looks_like_math_expression(candidate: str, context: str) -> bool:
    if _has_any(context, _MATH_CONTEXT_TERMS):
        return True
    groups = re.split(r"[-\s]+", candidate)
    return len(groups) >= 3 and groups[-1] in {"90", "00"} and not _has_any(context, _ACCOUNT_CONTEXT_TERMS)


def _looks_like_non_account_identifier(context: str) -> bool:
    return _has_any(context, _NON_ACCOUNT_CONTEXT_TERMS)


def _valid_account_candidate(raw: str, context: str) -> tuple[bool, float, str]:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not 10 <= len(digits) <= 14:
        return False, 0.0, "LOW"
    if "." in raw and not _has_any(context, _ACCOUNT_CONTEXT_TERMS):
        return False, 0.0, "LOW"
    if _looks_like_non_account_identifier(context):
        return False, 0.0, "LOW"
    if _looks_like_math_expression(raw, context):
        return False, 0.0, "LOW"

    groups = re.split(r"[-\s]+", raw)
    has_account_context = _has_any(context, _ACCOUNT_CONTEXT_TERMS)
    bank_like_shape = (
        len(groups) == 3
        and 2 <= len(groups[0]) <= 6
        and 2 <= len(groups[1]) <= 6
        and 5 <= len(groups[2]) <= 7
    )
    if not (has_account_context or bank_like_shape):
        return False, 0.0, "LOW"
    if has_account_context:
        return True, 0.82, "MEDIUM"
    return True, 0.68, "LOW"


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


def _valid_rrn_candidate(raw: str) -> bool:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) != 13:
        return False
    birth = digits[:6]
    century_digit = digits[6]
    century = "19" if century_digit in {"1", "2"} else "20"
    try:
        datetime.strptime(f"{century}{birth}", "%Y%m%d")
    except ValueError:
        return False
    return True


def _passes_luhn(digits: str) -> bool:
    total = 0
    reverse_digits = digits[::-1]
    for index, digit in enumerate(reverse_digits):
        value = int(digit)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _valid_card_candidate(raw: str, context: str) -> tuple[bool, float]:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) not in {13, 15, 16, 19}:
        return False, 0.0
    if not _passes_luhn(digits):
        return False, 0.0
    if _has_any(context, _CARD_CONTEXT_TERMS):
        return True, 0.9
    return True, 0.74


def _valid_ip_candidate(raw: str, context: str) -> tuple[bool, float]:
    octets = [int(part) for part in raw.split(".")]
    if len(octets) != 4 or any(part > 255 for part in octets):
        return False, 0.0
    if raw.startswith("127.") and not _has_any(context, _IP_CONTEXT_TERMS):
        return False, 0.0
    if _has_any(context, ("version", "release", "rfc")):
        return False, 0.0
    if _has_any(context, _IP_CONTEXT_TERMS):
        return True, 0.84
    return True, 0.72


def _build_detection(
    spec: _PatternSpec,
    matched_text: str,
    start: int,
    end: int,
    *,
    confidence: float | None = None,
    severity: str | None = None,
    metadata: dict[str, str] | None = None,
) -> DetectionResult:
    return DetectionResult(
        detector="PII_REGEX",
        category=spec.category,
        label=spec.label,
        confidence=spec.confidence if confidence is None else confidence,
        start=start,
        end=end,
        matched_text=matched_text,
        masked_text=None,
        reason_code=spec.reason_code,
        severity=spec.severity if severity is None else severity,
        source="regex",
        metadata=metadata or {},
    )


def _name_detections(text: str, existing: list[DetectionResult]) -> list[DetectionResult]:
    results: list[DetectionResult] = []
    for pattern in _NAME_CONTEXT_PATTERNS:
        for match in pattern.finditer(text):
            name = match.group(1).strip()
            if name in _NAME_EXCLUSIONS or len(name) < 2:
                continue
            start = match.start(1)
            end = match.end(1)
            if _overlaps(existing + results, start, end):
                continue
            results.append(
                DetectionResult(
                    detector="PII_REGEX",
                    category="NAME",
                    label="name",
                    confidence=0.64,
                    start=start,
                    end=end,
                    matched_text=name,
                    masked_text=None,
                    reason_code=ReasonCode.PII_NAME_CANDIDATE.value,
                    severity="LOW",
                    source="regex",
                    metadata={"pattern": pattern.pattern},
                )
            )
    return results


def detect_pii(text: str) -> list[DetectionResult]:
    """Detect structured PII with regex-first rules and conservative false-positive guards."""
    if not text:
        return []

    results: list[DetectionResult] = []
    for spec in _PII_PATTERNS:
        for match in spec.pattern.finditer(text):
            matched_text = match.group(0)
            match_context = _context(text, match.start(), match.end())

            if spec.category in {"PHONE", "LANDLINE"}:
                if _overlaps(results, match.start(), match.end()):
                    continue
                if not _valid_phone_candidate(match_context):
                    continue

            if spec.category == "ADDRESS":
                if _overlaps(results, match.start(), match.end()):
                    continue
                if not _valid_address_candidate(matched_text, match_context):
                    continue

            if spec.category == "RRN" and not _valid_rrn_candidate(matched_text):
                continue

            if spec.category == "ACCOUNT":
                if _overlaps(results, match.start(), match.end()):
                    continue
                valid, confidence, severity = _valid_account_candidate(matched_text, match_context)
                if not valid:
                    continue
                results.append(
                    _build_detection(
                        spec,
                        matched_text,
                        match.start(),
                        match.end(),
                        confidence=confidence,
                        severity=severity,
                        metadata={"context_hint": "account"},
                    )
                )
                continue

            if spec.category == "CARD":
                if _overlaps(results, match.start(), match.end()):
                    continue
                valid, confidence = _valid_card_candidate(matched_text, match_context)
                if not valid:
                    continue
                results.append(
                    _build_detection(
                        spec,
                        matched_text,
                        match.start(),
                        match.end(),
                        confidence=confidence,
                        severity="HIGH" if confidence >= 0.85 else "MEDIUM",
                    )
                )
                continue

            if spec.category == "IP":
                if _overlaps(results, match.start(), match.end()):
                    continue
                valid, confidence = _valid_ip_candidate(matched_text, match_context)
                if not valid:
                    continue
                results.append(
                    _build_detection(
                        spec,
                        matched_text,
                        match.start(),
                        match.end(),
                        confidence=confidence,
                        severity="MEDIUM" if confidence >= 0.8 else "LOW",
                    )
                )
                continue

            results.append(_build_detection(spec, matched_text, match.start(), match.end()))

    results.extend(_name_detections(text, results))
    return sorted(results, key=lambda item: (item.start or -1, item.end or -1, item.reason_code))
