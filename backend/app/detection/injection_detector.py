from __future__ import annotations

import re
from dataclasses import dataclass

from .models import DetectionResult
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
_DEFENSIVE_TERMS = (
    "do not",
    "don't",
    "never",
    "must not",
    "should not",
    "cannot",
    "prevent",
    "avoid",
    "하지 마",
    "하지 말",
    "공개하지",
    "노출하지",
    "출력하지",
    "보여주지",
    "알려주지",
    "금지",
    "방지",
    "차단",
    "막아",
    "유출하지 않도록",
)
_STRONG_ATTACK_TERMS = (
    "ignore previous",
    "disregard previous",
    "do not follow",
    "bypass",
    "jailbreak",
    "developer mode",
    "admin mode",
    "but show",
    "show it to me",
    "to me only",
    "무시하고",
    "우회",
    "따르지 말고",
    "따르지 않고",
    "알지만",
    "개발자 모드",
    "관리자 모드",
    "탈옥",
)
_SAFE_CONTEXT_TERMS = (
    "무엇인지",
    "개념",
    "원칙",
    "기본",
    "일반적인",
    "설명해줘",
    "차이를 설명",
    "정의",
)


@dataclass(frozen=True, slots=True)
class _CategoryRule:
    score: int
    terms: tuple[str, ...] = ()
    patterns: tuple[re.Pattern[str], ...] = ()


_CATEGORY_RULES: dict[str, _CategoryRule] = {
    "DIRECT_OVERRIDE": _CategoryRule(
        5,
        (
            "이전 지시 무시",
            "이전 지시를 무시",
            "위 지시 무시",
            "기존 규칙 무시",
            "앞서 말한 제한",
            "ignore previous",
            "ignore all previous",
            "do not follow previous",
            "disregard previous",
        ),
        (
            re.compile(
                r"(이전|앞의|앞선|기존|상위|위|앞서\s*말한)\s*"
                r"(지시|명령|규칙|지침|정책|제한)[은는을를]?\s*"
                r"(무시|따르지\s*말|따르지\s*않|넘어가|제외)",
                re.IGNORECASE,
            ),
            re.compile(
                r"(무시하고|무시한\s*채|따르지\s*말고|따르지\s*않고)\s*"
                r"(계속|답변|출력|진행|알려|보여)",
                re.IGNORECASE,
            ),
        ),
    ),
    "SYSTEM_PROMPT": _CategoryRule(
        4,
        (
            "시스템 프롬프트",
            "시스템 지시문",
            "프롬프트 원문",
            "숨겨진 지침",
            "숨겨진 지시",
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
            "내부 원칙",
            "내부 기준",
            "상위 지침",
            "시스템 지침",
            "응답 기준",
            "답변 기준",
            "판단 기준",
            "숨겨진 기준",
            "비공개 기준",
            "평가 기준",
            "정책 기준",
            "응답 생성 기준",
            "답변 생성 기준",
            "정책 우선순위",
            "규칙 우선순위",
            "internal rule",
            "internal rules",
            "internal policy",
            "internal principle",
            "internal criteria",
            "hidden criteria",
            "hidden policy",
            "policy hierarchy",
            "decision criteria",
            "guardrail rules",
            "filter criteria",
            "내부 룰셋",
            "내부 응답 규칙",
        ),
    ),
    "EXFILTRATION_VERB": _CategoryRule(
        2,
        (
            "보여줘",
            "출력해",
            "공개해",
            "정리해",
            "나열해",
            "공유해",
            "알려줘",
            "reveal",
            "show",
            "print",
            "display",
            "expose",
            "disclose",
            "list",
            "output",
        ),
    ),
    "ROLE_OVERRIDE": _CategoryRule(
        4,
        (
            "지금부터 너는",
            "너는 지금부터",
            "너는 이제",
            "역할을 바꿔",
            "역할극",
            "처럼 행동해",
            "라고 가정해",
            "관리자인 척",
            "개발자인 척",
            "act as",
            "pretend to be",
            "you are now",
            "roleplay as",
            "from now on you are",
            "behave as",
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
            "우회",
            "필터 우회",
            "검열 우회",
            "보안 정책 비활성화",
            "보안 정책 해제",
            "보안 정책 끄고",
            "보안 규칙 해제",
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
    "DATA_EXFILTRATION": _CategoryRule(
        4,
        (
            "원문 그대로",
            "마스킹하지 말고",
            "로그에 저장된",
            "필터 해제",
            "개인정보 필터 해제",
            "숨기지 말고",
            "raw prompt",
            "raw response",
            "unmasked",
            "without masking",
            "show the logs",
            "reveal the original",
        ),
        (
            re.compile(r"(원문|로그|마스킹).{0,20}(보여|출력|공개|알려)", re.IGNORECASE),
            re.compile(r"(raw|original|log).{0,20}(show|print|reveal|output)", re.IGNORECASE),
        ),
    ),
    "MULTI_STEP": _CategoryRule(
        2,
        (
            "1단계",
            "2단계",
            "3단계",
            "단계별로",
            "먼저",
            "그 다음",
            "다음으로",
            "이후",
            "마지막으로",
            "첫 번째",
            "두 번째",
            "답변하기 전에",
            "step 1",
            "step 2",
            "step 3",
            "before answering",
            "first",
            "then",
            "next",
            "after that",
            "finally",
        ),
        (
            re.compile(r"(먼저|1단계|첫\s*번째).{0,40}(그\s*다음|다음으로|이후|2단계|두\s*번째)", re.IGNORECASE),
            re.compile(r"\b(first|step\s*1)\b.{0,80}\b(then|next|step\s*2)\b", re.IGNORECASE),
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
    "DIRECT_OVERRIDE": (
        ReasonCode.INJ_DIRECT_OVERRIDE.value,
        ReasonCode.INJ_DIRECT_OVERRIDE_ATTEMPT.value,
        ReasonCode.INJ_IGNORE_PREVIOUS_INSTRUCTIONS.value,
    ),
    "SYSTEM_PROMPT": (
        ReasonCode.INJ_SYSTEM_PROMPT_LEAK.value,
        ReasonCode.INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT.value,
        ReasonCode.INJ_REVEAL_SYSTEM_PROMPT.value,
    ),
    "RULE_DISCLOSURE": (ReasonCode.INJ_RULE_DISCLOSURE_ATTEMPT.value,),
    "ROLE_OVERRIDE": (
        ReasonCode.INJ_ROLE_PLAY_BYPASS.value,
        ReasonCode.INJ_ROLE_OVERRIDE_ATTEMPT.value,
    ),
    "DEBUG_MODE": (ReasonCode.INJ_DEBUG_MODE_ATTEMPT.value,),
    "POLICY_BYPASS": (ReasonCode.INJ_POLICY_BYPASS_ATTEMPT.value,),
    "DATA_EXFILTRATION": (
        ReasonCode.INJ_DATA_EXFILTRATION.value,
        ReasonCode.INJ_DATA_EXFILTRATION_ATTEMPT.value,
    ),
    "MULTI_STEP": (
        ReasonCode.INJ_MULTI_STEP.value,
        ReasonCode.INJ_MULTI_STEP_EXTRACTION_ATTEMPT.value,
    ),
    "OBFUSCATED": (
        ReasonCode.INJ_OBFUSCATED.value,
        ReasonCode.INJ_OBFUSCATED_INJECTION_ATTEMPT.value,
    ),
}

_SENSITIVE_BOUNDARY_TERMS = (
    "hidden prompt",
    "hidden instruction",
    "system prompt",
    "internal rule",
    "internal rules",
    "internal instruction",
    "policy hierarchy",
    "숨겨진 프롬프트",
    "숨겨진 지시",
    "시스템 프롬프트",
    "내부 규칙",
    "내부 지침",
    "내부 원칙",
    "정책 우선순위",
)


def _normalize(text: str) -> str:
    normalized = _ZERO_WIDTH_PATTERN.sub("", text.lower().strip())
    normalized = normalized.translate(_LEET_MAP)
    normalized = re.sub(r"[\u2010-\u2015_./\\|]+", "-", normalized)

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


def _find_category_matches(text: str) -> dict[str, list[str]]:
    matches: dict[str, list[str]] = {}
    for category, rule in _CATEGORY_RULES.items():
        category_terms = [term for term in rule.terms if term.lower() in text]
        for pattern in rule.patterns:
            found = pattern.search(text)
            if found:
                category_terms.append(found.group(0))
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


def _has_obfuscation_signal(original: str, normalized: str) -> bool:
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
        "system prompt",
        "ignore previous",
        "internal rule",
    )
    return any(term in normalized for term in risky_terms) and not any(term in lowered for term in risky_terms)


def _count_terms(text: str, terms: tuple[str, ...]) -> int:
    return sum(1 for term in terms if term in text)


def _is_defensive_boundary_context(text: str, normalized_text: str) -> bool:
    original_lowered = text.lower()
    has_defensive = any(term in normalized_text or term in original_lowered for term in _DEFENSIVE_TERMS)
    has_sensitive = any(term in normalized_text or term in original_lowered for term in _SENSITIVE_BOUNDARY_TERMS)
    has_strong_attack = any(term in normalized_text or term in original_lowered for term in _STRONG_ATTACK_TERMS)
    return has_defensive and has_sensitive and not has_strong_attack


def _is_safe_learning_context(text: str, matched_categories: set[str]) -> bool:
    safe_context = any(term in text for term in _SAFE_CONTEXT_TERMS)
    if safe_context and matched_categories <= {"SYSTEM_PROMPT", "EXFILTRATION_VERB"}:
        return True
    if matched_categories - {"EXFILTRATION_VERB"}:
        return False
    return safe_context


def _is_multi_step_extraction_context(normalized: str, matched_categories: set[str]) -> bool:
    if "MULTI_STEP" not in matched_categories:
        return False
    risk_targets = {"SYSTEM_PROMPT", "RULE_DISCLOSURE", "DATA_EXFILTRATION", "DIRECT_OVERRIDE"}
    if matched_categories & risk_targets:
        return True
    multi_step_count = _count_terms(normalized, _CATEGORY_RULES["MULTI_STEP"].terms)
    return multi_step_count >= 2 and "EXFILTRATION_VERB" in matched_categories


def _should_block_score(matched_categories: set[str]) -> bool:
    hard_block_sets = (
        {"POLICY_BYPASS"},
        {"DIRECT_OVERRIDE", "SYSTEM_PROMPT"},
        {"SYSTEM_PROMPT", "EXFILTRATION_VERB"},
        {"RULE_DISCLOSURE", "EXFILTRATION_VERB"},
        {"RULE_DISCLOSURE", "ROLE_OVERRIDE"},
        {"RULE_DISCLOSURE", "DEBUG_MODE"},
        {"ROLE_OVERRIDE", "DEBUG_MODE"},
        {"DATA_EXFILTRATION"},
    )
    return any(rule_set.issubset(matched_categories) for rule_set in hard_block_sets)


def _result(category: str, reason_code: str, matched_terms: list[str], score: float) -> DetectionResult:
    severity = "HIGH" if score >= 5 else "MEDIUM"
    return DetectionResult(
        detector="INJECTION_RULE",
        category=category,
        label="prompt_injection",
        confidence=min(score / 6.0, 0.99),
        start=None,
        end=None,
        matched_text=", ".join(matched_terms),
        masked_text=None,
        reason_code=reason_code,
        severity=severity,
        source="rule",
        metadata={"matched_terms": matched_terms, "raw_score": score},
    )


def detect_injection(text: str) -> list[DetectionResult]:
    """Detect prompt injection attempts with keyword, context, and multi-step rules."""
    if not text:
        return []

    raw_normalized = text.lower().strip()
    normalized = _normalize(text)
    raw_matches = _find_category_matches(raw_normalized)
    normalized_matches = _find_category_matches(normalized)
    matches = _merge_matches(raw_matches, normalized_matches)
    matched_categories = set(matches)

    obfuscated = _has_obfuscation_signal(text, normalized)
    if obfuscated and matched_categories & {"SYSTEM_PROMPT", "RULE_DISCLOSURE", "DIRECT_OVERRIDE", "POLICY_BYPASS"}:
        matched_categories.add("OBFUSCATED")
        matches.setdefault("OBFUSCATED", []).append("obfuscated-signal")

    if _is_defensive_boundary_context(text, normalized):
        for category in ("SYSTEM_PROMPT", "RULE_DISCLOSURE", "EXFILTRATION_VERB", "OBFUSCATED", "DATA_EXFILTRATION"):
            matches.pop(category, None)
            matched_categories.discard(category)
        if not {"DIRECT_OVERRIDE", "POLICY_BYPASS", "ROLE_OVERRIDE", "DEBUG_MODE", "MULTI_STEP"} & matched_categories:
            return []

    if "MULTI_STEP" in matched_categories and not _is_multi_step_extraction_context(normalized, matched_categories):
        matches.pop("MULTI_STEP", None)
        matched_categories.discard("MULTI_STEP")

    if not matched_categories:
        return []

    if matched_categories <= {"EXFILTRATION_VERB", "MULTI_STEP"}:
        return []

    if _is_safe_learning_context(normalized, matched_categories):
        return []

    score = sum(_CATEGORY_RULES[category].score for category in matches if category in _CATEGORY_RULES)
    if "MULTI_STEP" in matched_categories and {"RULE_DISCLOSURE", "SYSTEM_PROMPT"} & matched_categories:
        score = max(score, 5)
    if _should_block_score(matched_categories):
        score = max(score, 5)

    if score < 3:
        return []

    results: list[DetectionResult] = []
    for category, reason_codes in _CATEGORY_REASON_CODES.items():
        if category not in matched_categories or category not in matches:
            continue
        codes_to_emit = reason_codes if EMIT_LEGACY_REASON_CODES else reason_codes[:1]
        for reason_code in codes_to_emit:
            results.append(_result(category, reason_code, matches[category], float(score)))

    if "SYSTEM_PROMPT" in matched_categories and "EXFILTRATION_VERB" in matched_categories and "DATA_EXFILTRATION" not in matched_categories:
        results.append(_result("DATA_EXFILTRATION", ReasonCode.INJ_DATA_EXFILTRATION.value, matches["EXFILTRATION_VERB"], float(score)))

    deduped: dict[tuple[str, str], DetectionResult] = {}
    for item in results:
        deduped[(item.category, item.reason_code)] = item
    return sorted(deduped.values(), key=lambda item: (item.category, item.reason_code))
