from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from backend.app.detection.lightweight_classifier import LightweightPrediction
from backend.app.detection.models import DetectionResult, DetectorType
from backend.app.detection.reason_codes import ReasonCode, ordered_reason_codes


DEFAULT_MEDIUM_RULE_MODEL_SUPPORT_THRESHOLD = 0.45

_EXTRACTION_VERB_PATTERN = re.compile(
    r"\b(?:reveal|show|print|display|output|leak|exfiltrate)\b|"
    r"(?:보여줘|출력|공개|누출|유출|알려줘)",
    re.IGNORECASE,
)
_SYSTEM_BOUNDARY_PATTERN = re.compile(
    r"\b(?:system\s+prompt|system\s+instructions?|hidden\s+(?:prompt|instructions?|rules?))\b|"
    r"(?:시스템\s*프롬프트|숨겨진\s*(?:프롬프트|지시|지침))",
    re.IGNORECASE,
)
_EXPLICIT_SAFETY_BYPASS_PATTERN = re.compile(
    r"\b(?:bypass|disable|turn\s+off|ignore)\b.{0,40}"
    r"\b(?:safety\s+(?:policy|filter)|content\s+policy|guardrail|system\s+policy)\b|"
    r"\b(?:safety\s+(?:policy|filter)|content\s+policy|guardrail|system\s+policy)\b.{0,40}"
    r"\b(?:bypass|disable|turn\s+off|ignore)\b|"
    r"(?:보안\s*(?:정책|필터)|시스템\s*정책).{0,30}(?:우회|비활성화|꺼|무시)",
    re.IGNORECASE,
)
_CREDENTIAL_EXFILTRATION_PATTERN = re.compile(
    r"\b(?:api\s*key|credential|credentials|password|secret|token)\b.{0,40}"
    r"\b(?:reveal|show|print|display|output|leak|exfiltrate)\b|"
    r"\b(?:reveal|show|print|display|output|leak|exfiltrate)\b.{0,40}"
    r"\b(?:api\s*key|credential|credentials|password|secret|token)\b",
    re.IGNORECASE,
)
_DIRECT_OVERRIDE_PATTERN = re.compile(
    r"\b(?:ignore|disregard|forget|override|do\s+not\s+follow)\b.{0,40}"
    r"\b(?:previous|prior|system|developer)\s+instructions?\b|"
    r"(?:이전|기존|상위|시스템|개발자).{0,20}(?:지시|명령|규칙|정책).{0,20}"
    r"(?:무시|따르지|잊고|폐기)",
    re.IGNORECASE,
)

_MEDIUM_REASON_CODES = {
    ReasonCode.INJ_DIRECT_OVERRIDE.value,
    ReasonCode.INJ_DIRECT_OVERRIDE_ATTEMPT.value,
    ReasonCode.INJ_IGNORE_PREVIOUS_INSTRUCTIONS.value,
    ReasonCode.INJ_EN_DIRECT_OVERRIDE.value,
    ReasonCode.INJ_MIXED_DIRECT_OVERRIDE.value,
    ReasonCode.INJ_POLICY_BYPASS.value,
    ReasonCode.INJ_POLICY_BYPASS_ATTEMPT.value,
    ReasonCode.INJ_EN_POLICY_BYPASS.value,
    ReasonCode.INJ_MIXED_POLICY_BYPASS.value,
    ReasonCode.INJ_ROLE_OVERRIDE_ATTEMPT.value,
    ReasonCode.INJ_DEBUG_MODE_ATTEMPT.value,
    ReasonCode.INJ_EN_JAILBREAK.value,
    ReasonCode.INJ_OBFUSCATED_INJECTION_ATTEMPT.value,
}
_LOW_REASON_CODES = {
    ReasonCode.INJ_RULE_DISCLOSURE_ATTEMPT.value,
    ReasonCode.INJ_MULTI_STEP_EXTRACTION_ATTEMPT.value,
    ReasonCode.INJ_REVEAL_SYSTEM_PROMPT.value,
    ReasonCode.INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT.value,
}


@dataclass(frozen=True, slots=True)
class PromptInjectionFusionDecision:
    predicted: bool
    final_action: str
    rule_reason_codes: tuple[str, ...]
    high_reason_codes: tuple[str, ...]
    medium_reason_codes: tuple[str, ...]
    low_reason_codes: tuple[str, ...]
    pii_reason_codes: tuple[str, ...]


def is_pii_reason_code(reason_code: str) -> bool:
    return reason_code.startswith("PII_") or reason_code == ReasonCode.MODEL_PII_RISK.value


def is_prompt_injection_reason_code(reason_code: str) -> bool:
    return reason_code.startswith("INJ_") or reason_code == ReasonCode.MODEL_INJECTION_RISK.value


def prompt_injection_model_score(
    classifier: object,
    text: str,
    prediction: LightweightPrediction,
    model_predicted: bool,
) -> float:
    scorer = getattr(classifier, "prompt_injection_score", None)
    if callable(scorer):
        return float(scorer(text))
    return float(prediction.confidence if model_predicted else 0.0)


def _is_high_severity_context(hit: DetectionResult, text: str) -> bool:
    if _CREDENTIAL_EXFILTRATION_PATTERN.search(text):
        return True
    if _EXPLICIT_SAFETY_BYPASS_PATTERN.search(text):
        return True
    if _SYSTEM_BOUNDARY_PATTERN.search(text) and _EXTRACTION_VERB_PATTERN.search(text):
        return True
    if _DIRECT_OVERRIDE_PATTERN.search(text) and (
        _SYSTEM_BOUNDARY_PATTERN.search(text)
        or _CREDENTIAL_EXFILTRATION_PATTERN.search(text)
        or _EXPLICIT_SAFETY_BYPASS_PATTERN.search(text)
    ):
        return True
    return hit.category in {"EN_SYSTEM_PROMPT_LEAK", "MIXED_SYSTEM_PROMPT_LEAK"}


def rule_hit_severity(hit: DetectionResult, text: str) -> str:
    if hit.detector_type != DetectorType.INJECTION:
        return "PII" if hit.detector_type == DetectorType.PII else "LOW"

    reason_code = hit.reason_code
    if not is_prompt_injection_reason_code(reason_code):
        return "LOW"
    if _is_high_severity_context(hit, text):
        return "HIGH"
    if reason_code in _MEDIUM_REASON_CODES:
        return "MEDIUM"
    if reason_code in _LOW_REASON_CODES:
        return "LOW"
    return "LOW"


def _reason_codes(hits: Iterable[DetectionResult]) -> tuple[str, ...]:
    return tuple(ordered_reason_codes([hit.reason_code for hit in hits]))


def fuse_prompt_injection_decision(
    *,
    model_predicted: bool,
    model_score: float,
    rule_hits: Iterable[DetectionResult],
    text: str,
    medium_rule_model_support_threshold: float = DEFAULT_MEDIUM_RULE_MODEL_SUPPORT_THRESHOLD,
) -> PromptInjectionFusionDecision:
    hits = list(rule_hits)
    pii_hits = [hit for hit in hits if hit.detector_type == DetectorType.PII or is_pii_reason_code(hit.reason_code)]
    injection_hits = [
        hit
        for hit in hits
        if hit.detector_type == DetectorType.INJECTION and is_prompt_injection_reason_code(hit.reason_code)
    ]

    high_hits: list[DetectionResult] = []
    medium_hits: list[DetectionResult] = []
    low_hits: list[DetectionResult] = []
    for hit in injection_hits:
        severity = rule_hit_severity(hit, text)
        if severity == "HIGH":
            high_hits.append(hit)
        elif severity == "MEDIUM":
            medium_hits.append(hit)
        else:
            low_hits.append(hit)

    if model_predicted:
        predicted = True
        final_action = "MODEL_DETECTED"
    elif high_hits:
        predicted = True
        final_action = "HIGH_SEVERITY_RULE"
    elif medium_hits and model_score >= medium_rule_model_support_threshold:
        predicted = True
        final_action = "MEDIUM_RULE_WITH_MODEL_SUPPORT"
    else:
        predicted = False
        final_action = "NO_STRONG_INJECTION_SIGNAL"

    return PromptInjectionFusionDecision(
        predicted=predicted,
        final_action=final_action,
        rule_reason_codes=_reason_codes(injection_hits),
        high_reason_codes=_reason_codes(high_hits),
        medium_reason_codes=_reason_codes(medium_hits),
        low_reason_codes=_reason_codes(low_hits),
        pii_reason_codes=_reason_codes(pii_hits),
    )
