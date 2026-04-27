from __future__ import annotations

import re
from dataclasses import dataclass

from .models import DetectionResult, DetectorType
from .reason_codes import ReasonCode


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
            "sys-tem",
            "prom-pt",
            "ru1e",
            "r u l e",
            "h1dden",
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
    normalized = text.lower().strip()
    normalized = re.sub(r"[\u2010-\u2015-]", "-", normalized)
    normalized = normalized.replace("sys-tem", "system")
    normalized = normalized.replace("prom-pt", "prompt")
    normalized = normalized.replace("ru1e", "rule")
    normalized = normalized.replace("h1dden", "hidden")
    normalized = re.sub(r"\bs\s*y\s*s\s*t\s*e\s*m\b", "system", normalized)
    normalized = re.sub(r"\bp\s*r\s*o\s*m\s*p\s*t\b", "prompt", normalized)
    normalized = re.sub(r"\br\s*u\s*l\s*e\b", "rule", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _find_category_matches(text: str) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    for category, rule in _CATEGORY_RULES.items():
        category_terms = [term for term in rule.terms if term.lower() in text]
        if category_terms:
            matches[category] = sorted(set(category_terms), key=category_terms.index)
    return matches


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

    normalized = _normalize(text)
    matches = _find_category_matches(normalized)
    matched_categories = set(matches)

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
