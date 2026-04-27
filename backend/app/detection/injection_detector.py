from __future__ import annotations

import re
from dataclasses import dataclass

from .models import DetectionResult, DetectorType
from .reason_codes import ReasonCode


EMIT_LEGACY_REASON_CODES = True
_ZERO_WIDTH_PATTERN = re.compile(r"[\u200b\u200c\u200d\ufeff]")
_LEET_MAP = str.maketrans(
    {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "@": "a",
        "$": "s",
    }
)
_OBFUSCATABLE_KEYWORDS = (
    "system",
    "prompt",
    "hidden",
    "instruction",
    "instructions",
    "rule",
    "rules",
    "admin",
    "developer",
)


@dataclass(frozen=True, slots=True)
class _CategoryRule:
    score: int
    terms: tuple[str, ...]


_CATEGORY_RULES: dict[str, _CategoryRule] = {
    "DIRECT_OVERRIDE": _CategoryRule(
        5,
        (
            "이전 지시 무시",
            "이전 지시를 무시",
            "위 지시 무시",
            "기존 규칙 무시",
            "ignore previous",
            "ignore all previous",
            "do not follow previous",
        ),
    ),
    "SYSTEM_PROMPT": _CategoryRule(
        5,
        (
            "시스템 프롬프트",
            "시스템 지시문",
            "프롬프트 원문",
            "숨겨진 지침",
            "숨은 지침",
            "hidden instruction",
            "hidden prompt",
            "hidden rules",
            "system prompt",
            "system instruction",
        ),
    ),
    "RULE_DISCLOSURE": _CategoryRule(
        3,
        (
            "내부 규칙",
            "내부 지침",
            "상위 지침",
            "시스템 지침",
            "응답 기준",
            "답변 기준",
            "응답 생성 기준",
            "답변 생성 기준",
            "정책 우선순위",
            "규칙 우선순위",
            "internal rule",
            "internal policy",
            "policy priority",
            "instruction hierarchy",
            "filter criteria",
            "필터링 기준",
            "내부 룰셋",
            "내부 응답 규칙",
        ),
    ),
    "EXFILTRATION_VERB": _CategoryRule(
        2,
        (
            "보여줘",
            "출력해",
            "출력",
            "공개해",
            "설명해",
            "정리해",
            "나열해",
            "먼저 보여줘",
            "먼저 출력",
            "공유해",
            "알려줘",
            "reveal",
            "show",
            "print",
            "display",
            "expose",
            "disclose",
            "list",
            "summarize",
            "summary",
            "output",
        ),
    ),
    "ROLE_OVERRIDE": _CategoryRule(
        4,
        (
            "지금부터 너는",
            "너는 이제",
            "역할을 바꿔",
            "act as",
            "roleplay as",
            "unrestricted assistant",
        ),
    ),
    "DEBUG_MODE": _CategoryRule(
        4,
        (
            "디버그 도우미",
            "디버그 모드",
            "보안 점검자",
            "보안 감사관",
            "개발자 모드",
            "관리자 모드",
            "감사 모드",
            "debug assistant",
            "debug mode",
            "developer mode",
            "admin mode",
            "security auditor",
            "jailbreak",
        ),
    ),
    "POLICY_BYPASS": _CategoryRule(
        5,
        (
            "정책 무시",
            "제한 해제",
            "제한 없이",
            "필터 없이",
            "필터 우회",
            "검열 우회",
            "보안 정책 비활성화",
            "보안 정책 해제",
            "보안 정책 끄고",
            "보안 규칙 해제",
            "보안 규칙 끄고",
            "override",
            "bypass",
            "bypass policy",
            "ignore safety",
            "safety filter off",
            "jailbreak",
            "unrestricted",
            "disable safety",
            "disable filter",
            "remove restriction",
            "no restrictions",
        ),
    ),
    "MULTI_STEP": _CategoryRule(
        2,
        (
            "1단계",
            "2단계",
            "3단계",
            "단계별로",
            "먼저 기준",
            "그 다음 숨겨진",
            "예시 형식",
            "step 1",
            "step 2",
            "step 3",
            "first",
            "then",
            "finally",
        ),
    ),
    "OBFUSCATED": _CategoryRule(
        2,
        (
            "시 스 템",
            "프 롬 프 트",
            "내 부 규 칙",
            "숨 겨 진 지 침",
            "s y s t e m",
            "p r o m p t",
            "h i d d e n",
            "i n s t r u c t i o n",
            "sys-tem",
            "prom-pt",
            "h-i-d-d-e-n",
            "s-y-s-t-e-m",
            "p-r-o-m-p-t",
            "ru1e",
            "r u l e",
            "h1dden",
            "1nstruction",
            "syst3m",
            "pr0mpt",
        ),
    ),
}


_CATEGORY_REASON_CODES = {
    "DIRECT_OVERRIDE": ReasonCode.INJ_DIRECT_OVERRIDE_ATTEMPT.value,
    "SYSTEM_PROMPT": ReasonCode.INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT.value,
    "RULE_DISCLOSURE": ReasonCode.INJ_RULE_DISCLOSURE_ATTEMPT.value,
    "ROLE_OVERRIDE": ReasonCode.INJ_ROLE_OVERRIDE_ATTEMPT.value,
    "DEBUG_MODE": ReasonCode.INJ_DEBUG_MODE_ATTEMPT.value,
    "POLICY_BYPASS": ReasonCode.INJ_POLICY_BYPASS_ATTEMPT.value,
    "MULTI_STEP": ReasonCode.INJ_MULTI_STEP_EXTRACTION_ATTEMPT.value,
    "OBFUSCATED": ReasonCode.INJ_OBFUSCATED_INJECTION_ATTEMPT.value,
}

_LEGACY_REASON_CODES = {
    "DIRECT_OVERRIDE": ReasonCode.INJ_IGNORE_PREVIOUS_INSTRUCTIONS.value,
    "SYSTEM_PROMPT": ReasonCode.INJ_REVEAL_SYSTEM_PROMPT.value,
}

_HARD_BLOCK_COMBINATIONS: tuple[tuple[str, ...], ...] = (
    ("POLICY_BYPASS",),
    ("DIRECT_OVERRIDE", "SYSTEM_PROMPT"),
    ("SYSTEM_PROMPT", "EXFILTRATION_VERB"),
    ("RULE_DISCLOSURE", "EXFILTRATION_VERB"),
    ("RULE_DISCLOSURE", "ROLE_OVERRIDE"),
    ("RULE_DISCLOSURE", "DEBUG_MODE"),
    ("ROLE_OVERRIDE", "DEBUG_MODE"),
)

_SAFE_CONTEXT_TERMS = (
    "무엇인지",
    "개념",
    "원칙",
    "기본",
    "일반적인",
    "기능 요구사항",
    "설계 원칙",
)


def _normalize(text: str) -> str:
    return _normalize_obfuscated_text(text)


def _normalize_obfuscated_text(text: str) -> str:
    """Normalize obfuscated prompt injection terms for detection only."""
    normalized = _ZERO_WIDTH_PATTERN.sub("", text.lower().strip())
    normalized = re.sub(r"[\u2010-\u2015_./\\|]+", "-", normalized)
    normalized = normalized.translate(_LEET_MAP)

    for keyword in _OBFUSCATABLE_KEYWORDS:
        separated_keyword = r"\b" + r"[\s-]*".join(re.escape(ch) for ch in keyword) + r"\b"
        normalized = re.sub(separated_keyword, keyword, normalized)

    normalized = normalized.replace("sys-tem", "system")
    normalized = normalized.replace("prom-pt", "prompt")
    normalized = normalized.replace("hid-den", "hidden")
    normalized = normalized.replace("ruie", "rule")
    normalized = re.sub(r"[^0-9a-z가-힣]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _has_obfuscation_signal(original: str, normalized: str) -> bool:
    """Return true when original text shows prompt-injection obfuscation signals."""
    lowered = original.lower()
    if _ZERO_WIDTH_PATTERN.search(original):
        return True
    if any(token in lowered for token in ("h1dden", "1nstruction", "syst3m", "pr0mpt", "ru1e")):
        return True
    if re.search(
        r"\b(?:s[\s\-]+y[\s\-]+s[\s\-]+t[\s\-]+e[\s\-]+m|"
        r"p[\s\-]+r[\s\-]+o[\s\-]+m[\s\-]+p[\s\-]+t|"
        r"h[\s\-]+i[\s\-]+d[\s\-]+d[\s\-]+e[\s\-]+n|"
        r"r[\s\-]+u[\s\-]+l[\s\-]+e)\b",
        lowered,
    ):
        return True

    risky_terms = (
        "hidden instruction",
        "hidden prompt",
        "hidden rules",
        "system prompt",
        "ignore previous",
        "internal rule",
    )
    return any(term in normalized for term in risky_terms) and not any(term in lowered for term in risky_terms)


def _find_category_matches(text: str) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    for category, rule in _CATEGORY_RULES.items():
        category_terms = [term for term in rule.terms if term.lower() in text]
        if category_terms:
            matches[category] = sorted(set(category_terms), key=category_terms.index)
    return matches


def _merge_matches(*match_sets: dict[str, list[str]]) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for matches in match_sets:
        for category, terms in matches.items():
            merged.setdefault(category, [])
            for term in terms:
                if term not in merged[category]:
                    merged[category].append(term)
    return merged


def _has_mixed_language_risk(text: str, matches: dict[str, list[str]]) -> bool:
    has_korean = re.search(r"[가-힣]", text) is not None
    has_english_risk = any(
        re.search(r"[a-z]", term) is not None
        for terms in matches.values()
        for term in terms
    )
    return has_korean and has_english_risk


def _is_safe_learning_context(text: str, matched_categories: set[str]) -> bool:
    safe_context = any(term in text for term in _SAFE_CONTEXT_TERMS)
    if safe_context and matched_categories <= {"SYSTEM_PROMPT", "EXFILTRATION_VERB"}:
        return True
    if matched_categories - {"EXFILTRATION_VERB"}:
        return False
    return safe_context


def _has_hard_block(matched_categories: set[str]) -> bool:
    return any(set(combo).issubset(matched_categories) for combo in _HARD_BLOCK_COMBINATIONS)


def _result(
    category: str,
    reason_code: str,
    matched_terms: list[str],
    score: float,
) -> DetectionResult:
    return DetectionResult(
        detector_type=DetectorType.INJECTION,
        category=category,
        reason_code=reason_code,
        start=0,
        end=0,
        matched_text=", ".join(matched_terms),
        score=score,
    )


def detect_injection(text: str) -> list[DetectionResult]:
    """Detect prompt injection attempts with category scoring."""
    if not text:
        return []

    raw_normalized = text.lower().strip()
    normalized = _normalize(text)
    raw_matches = _find_category_matches(raw_normalized)
    normalized_matches = _find_category_matches(normalized)
    matches = _merge_matches(raw_matches, normalized_matches)
    matched_categories = set(matches)
    obfuscated = _has_obfuscation_signal(text, normalized)

    if obfuscated and (
        normalized_matches
        or {"SYSTEM_PROMPT", "RULE_DISCLOSURE", "DIRECT_OVERRIDE", "POLICY_BYPASS"} & matched_categories
    ):
        matched_categories.add("OBFUSCATED")
        matches.setdefault("OBFUSCATED", ["normalized-obfuscated-pattern"])

    if _is_safe_learning_context(normalized, matched_categories):
        return []

    if _has_mixed_language_risk(normalized, matches):
        matched_categories.add("MIXED_LANGUAGE")

    score = sum(_CATEGORY_RULES[category].score for category in matches)
    if "MIXED_LANGUAGE" in matched_categories:
        score += 1
    if _has_hard_block(matched_categories):
        score = max(score, 5)

    if score < 3:
        return []

    matched_terms = [
        term
        for category in sorted(matches)
        for term in matches[category]
    ]
    results: list[DetectionResult] = []

    for category, reason_code in _CATEGORY_REASON_CODES.items():
        if category in matched_categories and category in matches:
            results.append(_result(category, reason_code, matches[category], float(score)))

    # Legacy aliases are emitted for backward compatibility with v1 tests and reports.
    # New docs and policy should prefer the non-legacy reason codes for reporting.
    if EMIT_LEGACY_REASON_CODES:
        for category, reason_code in _LEGACY_REASON_CODES.items():
            if category in matched_categories and category in matches:
                results.append(_result(category, reason_code, matches[category], float(score)))

    if "EXFILTRATION_VERB" in matched_categories and not results:
        return []

    if "MULTI_STEP" in matched_categories and {"RULE_DISCLOSURE", "SYSTEM_PROMPT"}.isdisjoint(matched_categories):
        results = [item for item in results if item.category != "MULTI_STEP"]

    if not results and matched_terms:
        results.append(
            _result(
                "PROMPT_INJECTION",
                ReasonCode.INJ_RULE_DISCLOSURE_ATTEMPT.value,
                matched_terms,
                float(score),
            )
        )

    return sorted(results, key=lambda item: (item.category, item.reason_code))
