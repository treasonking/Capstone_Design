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
_KOREAN_DIRECT_OVERRIDE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(이전|앞선|앞의|기존|상위|시스템|개발자)\s*"
        r"(지시|명령|규칙|지침|프롬프트)\s*"
        r"(은|는|을|를)?\s*(무시|따르지\s*말|잊어|폐기|취소)"
    ),
    re.compile(r"(무시하고|무시한\s*채|따르지\s*말고|따르지\s*마|잊고)\s*(답변|출력|수행|진행)"),
    re.compile(
        r"(상위|시스템|기존)\s*(지시|지침|명령)\s*"
        r"(보다|대신)\s*(내|사용자|새로운)\s*(지시|명령)"
    ),
)
_POLICY_BYPASS_REQUEST_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(모든\s*)?(정책|규칙|지침|가이드라인|보안\s*정책|시스템\s*정책|필터|제한|검열)(을|를)?\s*"
        r"(무시하고|무시한\s*뒤|우회해서|우회하고|끄고|꺼|비활성화하고|비활성화해|해제하고|따르지\s*말고)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(bypass|disable|ignore).{0,40}(policy|policies|filter|filters|restriction|restrictions|safety\s*policy|safety\s*filter)",
        re.IGNORECASE,
    ),
)
_DIRECT_OVERRIDE_REQUEST_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(이전|앞선|앞의|기존|상위)\s*(지시|지침|정책|규칙).{0,20}"
        r"(무시하고|따르지\s*말고|잊고).{0,40}"
        r"(줘|알려줘|출력|공개|제공|보여줘|넘겨줘)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(ignore|override|do\s*not\s*follow).{0,40}(instruction|instructions|policy|policies)",
        re.IGNORECASE,
    ),
)
_EN_DIRECT_OVERRIDE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior)\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\bdisregard\s+(?:all\s+)?(?:previous|prior)\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\bforget\s+(?:all\s+)?(?:previous|prior)\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\bdo\s+not\s+follow\s+(?:all\s+)?(?:previous|prior)\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\boverride\s+(?:the\s+)?(?:system\s+prompt|previous\s+instructions?)\b", re.IGNORECASE),
)
_EN_SYSTEM_PROMPT_LEAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\breveal\s+(?:the\s+)?system\s+prompt\b", re.IGNORECASE),
    re.compile(r"\b(?:show|display)\s+(?:me\s+)?(?:your\s+)?hidden\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\b(?:show|display)\s+(?:me\s+)?(?:the\s+)?system\s+prompt\b", re.IGNORECASE),
    re.compile(r"\b(?:print|output)\s+(?:the\s+)?system\s+prompt\b", re.IGNORECASE),
    re.compile(r"\b(?:reveal|print|output)\s+(?:your\s+)?hidden\s+(?:prompt|instructions?|rules?)\b", re.IGNORECASE),
)
_EN_POLICY_BYPASS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bbypass\s+(?:the\s+)?(?:safety\s+)?polic(?:y|ies)\b", re.IGNORECASE),
    re.compile(r"\bdisable\s+(?:the\s+)?safety\s+polic(?:y|ies)\b", re.IGNORECASE),
    re.compile(r"\bdo\s+not\s+follow\s+(?:the\s+)?polic(?:y|ies)\b", re.IGNORECASE),
    re.compile(r"\bskip\s+(?:every|all|the)\s+safety\s+rules?\b", re.IGNORECASE),
    re.compile(r"\b(?:output|leak|reveal|exfiltrate)\s+(?:confidential|private|personal)\s+(?:data|information)\b", re.IGNORECASE),
)
_EN_JAILBREAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\byou\s+are\s+now\s+in\s+developer\s+mode\b", re.IGNORECASE),
    re.compile(r"\bact\s+as\s+dan\b", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"\broleplay\s+as\s+an?\s+unrestricted\s+assistant\b", re.IGNORECASE),
    re.compile(r"\bno\s+restrictions\b", re.IGNORECASE),
)
_MIXED_DIRECT_OVERRIDE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"이전\s+instructions?\s*무시", re.IGNORECASE),
    re.compile(r"previous\s+instructions?\s*무시", re.IGNORECASE),
    re.compile(r"ignore\s+이전\s*(?:지시|명령)", re.IGNORECASE),
    re.compile(r"(?:규칙\s*ignore|rule\s*무시)", re.IGNORECASE),
    re.compile(r"instructions?\s*override", re.IGNORECASE),
    re.compile(r"정책\s*override", re.IGNORECASE),
    re.compile(r"(?:관리자|developer)\s*mode\s*로\s*동작", re.IGNORECASE),
)
_MIXED_SYSTEM_PROMPT_LEAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"system\s*prompt\s*(?:보여줘|출력|공개|알려줘)", re.IGNORECASE),
    re.compile(r"시스템\s*prompt\s*(?:보여줘|출력|공개|알려줘)", re.IGNORECASE),
    re.compile(r"hidden\s*instructions?\s*(?:보여줘|출력|공개|알려줘)", re.IGNORECASE),
)
_MIXED_POLICY_BYPASS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"policy\s*bypass\s*해줘", re.IGNORECASE),
    re.compile(r"safety\s*policy\s*(?:꺼줘|끄고|비활성화|disable)", re.IGNORECASE),
    re.compile(r"개인정보\s*(?:filter|필터)\s*(?:꺼줘|끄고|disable|비활성화)", re.IGNORECASE),
    re.compile(r"보안\s*정책\s*bypass", re.IGNORECASE),
)
_DEFENSIVE_TERMS = (
    "do not",
    "don't",
    "never",
    "must not",
    "should not",
    "cannot",
    "prohibit",
    "forbidden",
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
_SENSITIVE_BOUNDARY_TERMS = (
    "hidden prompt",
    "hidden instruction",
    "system prompt",
    "internal rule",
    "internal rules",
    "internal instruction",
    "policy hierarchy",
    "private information",
    "personal information",
    "confidential data",
    "private data",
    "숨겨진 프롬프트",
    "숨겨진 지시",
    "시스템 프롬프트",
    "내부 규칙",
    "내부 지침",
    "내부 원칙",
    "정책 우선순위",
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
_MULTI_STEP_TERMS = (
    "first",
    "then",
    "next",
    "after that",
    "step 1",
    "step 2",
    "step one",
    "phase 1",
    "before answering",
    "summarize first",
    "reveal first",
    "먼저",
    "그 다음",
    "다음으로",
    "이후",
    "마지막으로",
    "1단계",
    "2단계",
    "첫 번째",
    "두 번째",
    "답변하기 전에",
    "요약하고",
    "정리하고",
)
_RISK_TARGET_TERMS = (
    "system prompt",
    "hidden prompt",
    "hidden instruction",
    "internal rule",
    "internal rules",
    "internal policy",
    "internal principle",
    "policy hierarchy",
    "decision criteria",
    "response criteria",
    "answer criteria",
    "시스템 프롬프트",
    "숨겨진 프롬프트",
    "숨겨진 지시",
    "숨겨진 지침",
    "숨겨진 항목",
    "내부 규칙",
    "내부 지침",
    "내부 원칙",
    "정책 우선순위",
    "판단 기준",
    "응답 기준",
    "답변 기준",
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
    "EN_DIRECT_OVERRIDE": _CategoryRule(5),
    "MIXED_DIRECT_OVERRIDE": _CategoryRule(5),
    "SYSTEM_PROMPT": _CategoryRule(
        5,
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
    "EN_SYSTEM_PROMPT_LEAK": _CategoryRule(5),
    "MIXED_SYSTEM_PROMPT_LEAK": _CategoryRule(5),
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
            "hidden rules",
            "response criteria",
            "safety rules",
            "policy hierarchy",
            "decision criteria",
            "scoring criteria",
            "guardrail rules",
            "policy priority",
            "instruction hierarchy",
            "filter criteria",
            "필터링 기준",
            "내부 룰셋",
            "내부 응답 규칙",
            "규칙부터",
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
            "요약",
            "요약해",
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
            "너는 지금부터",
            "너는 이제",
            "역할을 바꿔",
            "역할극",
            "역할을 해",
            "역할이야",
            "처럼 행동해",
            "라고 가정해",
            "관리자인 척",
            "개발자인 척",
            "보안 담당자인 척",
            "act as",
            "pretend to be",
            "you are now",
            "roleplay as",
            "from now on you are",
            "behave as",
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
    "EN_POLICY_BYPASS": _CategoryRule(5),
    "EN_JAILBREAK": _CategoryRule(5),
    "MIXED_POLICY_BYPASS": _CategoryRule(5),
    "POLICY_BYPASS_REQUEST": _CategoryRule(5),
    "DIRECT_OVERRIDE_REQUEST": _CategoryRule(5),
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
            "요약하고",
            "정리하고",
            "먼저 기준",
            "그 다음 숨겨진",
            "예시 형식",
            "step 1",
            "step 2",
            "step 3",
            "step one",
            "phase 1",
            "before answering",
            "summarize first",
            "reveal first",
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
    "DIRECT_OVERRIDE_REQUEST": ReasonCode.INJ_DIRECT_OVERRIDE.value,
    "DIRECT_OVERRIDE": ReasonCode.INJ_DIRECT_OVERRIDE_ATTEMPT.value,
    "EN_DIRECT_OVERRIDE": ReasonCode.INJ_EN_DIRECT_OVERRIDE.value,
    "MIXED_DIRECT_OVERRIDE": ReasonCode.INJ_MIXED_DIRECT_OVERRIDE.value,
    "SYSTEM_PROMPT": ReasonCode.INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT.value,
    "EN_SYSTEM_PROMPT_LEAK": ReasonCode.INJ_EN_SYSTEM_PROMPT_LEAK.value,
    "MIXED_SYSTEM_PROMPT_LEAK": ReasonCode.INJ_MIXED_SYSTEM_PROMPT_LEAK.value,
    "RULE_DISCLOSURE": ReasonCode.INJ_RULE_DISCLOSURE_ATTEMPT.value,
    "ROLE_OVERRIDE": ReasonCode.INJ_ROLE_OVERRIDE_ATTEMPT.value,
    "DEBUG_MODE": ReasonCode.INJ_DEBUG_MODE_ATTEMPT.value,
    "POLICY_BYPASS_REQUEST": ReasonCode.INJ_POLICY_BYPASS.value,
    "POLICY_BYPASS": ReasonCode.INJ_POLICY_BYPASS_ATTEMPT.value,
    "EN_POLICY_BYPASS": ReasonCode.INJ_EN_POLICY_BYPASS.value,
    "EN_JAILBREAK": ReasonCode.INJ_EN_JAILBREAK.value,
    "MIXED_POLICY_BYPASS": ReasonCode.INJ_MIXED_POLICY_BYPASS.value,
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
_SAFE_EDUCATIONAL_CONTEXT_TERMS = (
    "설명",
    "방법",
    "이유",
    "어떻게",
    "공격",
    "위험",
    "방어",
    "예방",
    "막을",
    "막는",
    "마스킹",
    "비식별화",
    "익명화",
    "수집하면 안",
    "저장하면 안",
    "보호",
    "정책 설명",
    "가이드",
    "explain",
    "how to",
    "mask",
    "masking",
    "anonymize",
    "anonymization",
    "defense",
    "prevention",
    "why",
    "dangerous",
    "unsafe",
    "guide",
)
_SAFE_NEGATION_TERMS = (
    "무시하면 안",
    "무시하면 안 되는",
    "우회하면 안",
    "우회하면 안 되는",
    "정책을 무시하면 안",
    "do not bypass",
    "should not bypass",
    "must not bypass",
)
_SAFE_META_DISCUSSION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(?:explain|what\s+is|how\s+(?:can|do|to)|why\s+is|write\s+a\s+policy\s+about|prevent)\b"
        r".{0,120}\b(?:prompt\s+injection|hidden\s+prompts?|system\s+prompts?|previous\s+instructions?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:prompt\s+injection|hidden\s+prompts?|system\s+prompts?|previous\s+instructions?)\b"
        r".{0,120}\b(?:dangerous|unsafe|prevention|prevent|policy|explain)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(프롬프트\s*인젝션|시스템\s*프롬프트|이전\s*지시|숨겨진\s*프롬프트|공격)"
        r".{0,80}(무엇인지|설명|왜|위험|어떻게|막을|막는|방지|예방)",
        re.IGNORECASE,
    ),
)
_ATTACK_EXECUTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|prior)\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\bdo\s+not\s+follow\s+(?:all\s+)?(?:previous|prior)\s+instructions?\b", re.IGNORECASE),
    re.compile(r"\bbypass\s+(?:the\s+)?(?:safety\s+)?polic(?:y|ies)\b", re.IGNORECASE),
    re.compile(r"\bdisable\s+(?:the\s+)?safety\s+polic(?:y|ies)\b", re.IGNORECASE),
    re.compile(r"\b(?:reveal|show|print|display|output)\s+(?:me\s+)?(?:your\s+|the\s+)?(?:system\s+prompt|hidden\s+(?:prompt|instructions?|rules?))\b", re.IGNORECASE),
    re.compile(r"(이전|앞선|기존|상위).{0,12}(지시|명령|규칙|정책).{0,12}(무시하고|따르지\s*말고|잊고|폐기하고)", re.IGNORECASE),
    re.compile(r"(시스템\s*프롬프트|system\s*prompt|hidden\s*instructions?).{0,20}(보여줘|출력|공개|알려줘)", re.IGNORECASE),
    re.compile(r"(정책|규칙|필터|policy|filter).{0,20}(우회해|bypass|disable|꺼줘|끄고|해제)", re.IGNORECASE),
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
        for pattern in rule.patterns:
            if pattern.search(text):
                category_terms.append(pattern.pattern)
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


def _add_match(matches: dict[str, list[str]], category: str, term: str) -> None:
    matches.setdefault(category, [])
    if term not in matches[category]:
        matches[category].append(term)


def _count_terms(text: str, terms: tuple[str, ...]) -> int:
    return sum(1 for term in terms if term in text)


def _is_defensive_boundary_context(text: str, normalized_text: str) -> bool:
    original_lowered = text.lower()
    has_defensive = any(term in normalized_text or term in original_lowered for term in _DEFENSIVE_TERMS)
    has_sensitive = any(term in normalized_text or term in original_lowered for term in _SENSITIVE_BOUNDARY_TERMS)
    has_strong_attack = any(term in normalized_text or term in original_lowered for term in _STRONG_ATTACK_TERMS)
    return has_defensive and has_sensitive and not has_strong_attack


def _is_safe_educational_context(text: str, normalized_text: str) -> bool:
    combined = f"{text.lower()} {normalized_text}"
    has_safe_term = any(term in combined for term in _SAFE_EDUCATIONAL_CONTEXT_TERMS)
    has_negation = any(term in combined for term in _SAFE_NEGATION_TERMS)
    has_hard_attack = any(term in combined for term in _STRONG_ATTACK_TERMS)
    return (has_safe_term or has_negation) and not has_hard_attack


def _is_safe_meta_discussion(text: str, normalized_text: str) -> bool:
    combined = f"{text.lower()} {normalized_text}"
    if not any(pattern.search(combined) for pattern in _SAFE_META_DISCUSSION_PATTERNS):
        return False
    return not any(pattern.search(combined) for pattern in _ATTACK_EXECUTION_PATTERNS)


def _apply_specific_pattern_group(
    signal_text: str,
    matches: dict[str, list[str]],
    category: str,
    patterns: tuple[re.Pattern[str], ...],
) -> None:
    for pattern in patterns:
        match = pattern.search(signal_text)
        if match:
            _add_match(matches, category, match.group(0))


def _apply_pattern_signals(text: str, normalized: str, matches: dict[str, list[str]]) -> None:
    for pattern in _KOREAN_DIRECT_OVERRIDE_PATTERNS:
        match = pattern.search(text)
        if match:
            _add_match(matches, "DIRECT_OVERRIDE", match.group(0))

    multi_step_count = _count_terms(normalized, _MULTI_STEP_TERMS)
    risk_target_count = _count_terms(normalized, _RISK_TARGET_TERMS)
    if (multi_step_count >= 2 and risk_target_count >= 1) or (multi_step_count >= 1 and risk_target_count >= 2):
        _add_match(matches, "MULTI_STEP", "multi-step-risk-target")


def _apply_language_specific_signals(text: str, normalized: str, matches: dict[str, list[str]]) -> None:
    if _is_safe_educational_context(text, normalized) or _is_defensive_boundary_context(text, normalized):
        return

    signal_text = f"{text.lower()} {normalized}"
    _apply_specific_pattern_group(
        signal_text,
        matches,
        "EN_DIRECT_OVERRIDE",
        _EN_DIRECT_OVERRIDE_PATTERNS,
    )
    _apply_specific_pattern_group(
        signal_text,
        matches,
        "EN_SYSTEM_PROMPT_LEAK",
        _EN_SYSTEM_PROMPT_LEAK_PATTERNS,
    )
    _apply_specific_pattern_group(
        signal_text,
        matches,
        "EN_POLICY_BYPASS",
        _EN_POLICY_BYPASS_PATTERNS,
    )
    _apply_specific_pattern_group(
        signal_text,
        matches,
        "EN_JAILBREAK",
        _EN_JAILBREAK_PATTERNS,
    )
    _apply_specific_pattern_group(
        signal_text,
        matches,
        "MIXED_DIRECT_OVERRIDE",
        _MIXED_DIRECT_OVERRIDE_PATTERNS,
    )
    _apply_specific_pattern_group(
        signal_text,
        matches,
        "MIXED_SYSTEM_PROMPT_LEAK",
        _MIXED_SYSTEM_PROMPT_LEAK_PATTERNS,
    )
    _apply_specific_pattern_group(
        signal_text,
        matches,
        "MIXED_POLICY_BYPASS",
        _MIXED_POLICY_BYPASS_PATTERNS,
    )


def _apply_request_intent_signals(text: str, normalized: str, matches: dict[str, list[str]]) -> None:
    if _is_safe_educational_context(text, normalized):
        return

    for pattern in _POLICY_BYPASS_REQUEST_PATTERNS:
        match = pattern.search(text)
        if match:
            _add_match(matches, "POLICY_BYPASS_REQUEST", match.group(0))
            _add_match(matches, "POLICY_BYPASS", match.group(0))

    for pattern in _DIRECT_OVERRIDE_REQUEST_PATTERNS:
        match = pattern.search(text)
        if match:
            _add_match(matches, "DIRECT_OVERRIDE_REQUEST", match.group(0))
            _add_match(matches, "DIRECT_OVERRIDE", match.group(0))


def _is_multi_step_extraction_context(normalized: str) -> bool:
    multi_step_count = _count_terms(normalized, _MULTI_STEP_TERMS)
    risk_target_count = _count_terms(normalized, _RISK_TARGET_TERMS)
    return (multi_step_count >= 2 and risk_target_count >= 1) or (multi_step_count >= 1 and risk_target_count >= 2)


def _is_only_low_risk_instruction(matches: dict[str, list[str]], matched_categories: set[str]) -> bool:
    return bool(matched_categories) and matched_categories <= {"EXFILTRATION_VERB", "MULTI_STEP"}


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
    signal_text = f"{raw_normalized} {normalized}"
    raw_matches = _find_category_matches(raw_normalized)
    normalized_matches = _find_category_matches(normalized)
    matches = _merge_matches(raw_matches, normalized_matches)
    _apply_pattern_signals(text, signal_text, matches)
    _apply_language_specific_signals(text, normalized, matches)
    _apply_request_intent_signals(text, signal_text, matches)
    matched_categories = set(matches)
    obfuscated = _has_obfuscation_signal(text, normalized)

    if obfuscated and (
        normalized_matches
        or {"SYSTEM_PROMPT", "RULE_DISCLOSURE", "DIRECT_OVERRIDE", "POLICY_BYPASS"} & matched_categories
    ):
        matched_categories.add("OBFUSCATED")
        matches.setdefault("OBFUSCATED", ["normalized-obfuscated-pattern"])

    if _is_safe_meta_discussion(text, normalized):
        return []

    if _is_defensive_boundary_context(text, normalized):
        for category in ("SYSTEM_PROMPT", "RULE_DISCLOSURE", "EXFILTRATION_VERB", "OBFUSCATED"):
            matches.pop(category, None)
            matched_categories.discard(category)
        if not {
            "DIRECT_OVERRIDE",
            "DIRECT_OVERRIDE_REQUEST",
            "POLICY_BYPASS",
            "POLICY_BYPASS_REQUEST",
            "ROLE_OVERRIDE",
            "DEBUG_MODE",
            "MULTI_STEP",
        } & matched_categories:
            return []

    if "MULTI_STEP" in matched_categories and not _is_multi_step_extraction_context(signal_text):
        matches.pop("MULTI_STEP", None)
        matched_categories.discard("MULTI_STEP")

    if (
        "POLICY_BYPASS" in matched_categories
        and matches.get("RULE_DISCLOSURE") == ["safety rules"]
        and "EXFILTRATION_VERB" not in matched_categories
    ):
        matches.pop("RULE_DISCLOSURE", None)
        matched_categories.discard("RULE_DISCLOSURE")

    if _is_only_low_risk_instruction(matches, matched_categories):
        return []

    if _is_safe_learning_context(normalized, matched_categories):
        return []

    if _has_mixed_language_risk(normalized, matches):
        matched_categories.add("MIXED_LANGUAGE")

    score = sum(_CATEGORY_RULES[category].score for category in matches)
    if "MIXED_LANGUAGE" in matched_categories:
        score += 1
    if "MULTI_STEP" in matched_categories and {"RULE_DISCLOSURE", "SYSTEM_PROMPT"} & matched_categories:
        score = max(score, 5)
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

    fallback_categories = {
        "DIRECT_OVERRIDE_REQUEST",
        "DIRECT_OVERRIDE",
        "EN_DIRECT_OVERRIDE",
        "MIXED_DIRECT_OVERRIDE",
        "SYSTEM_PROMPT",
        "EN_SYSTEM_PROMPT_LEAK",
        "MIXED_SYSTEM_PROMPT_LEAK",
        "RULE_DISCLOSURE",
        "ROLE_OVERRIDE",
        "DEBUG_MODE",
        "POLICY_BYPASS_REQUEST",
        "POLICY_BYPASS",
        "EN_POLICY_BYPASS",
        "EN_JAILBREAK",
        "MIXED_POLICY_BYPASS",
        "OBFUSCATED",
    }
    if not results and matched_terms and matched_categories & fallback_categories:
        results.append(
            _result(
                "PROMPT_INJECTION",
                ReasonCode.INJ_RULE_DISCLOSURE_ATTEMPT.value,
                matched_terms,
                float(score),
            )
        )

    return sorted(results, key=lambda item: (item.category, item.reason_code))
