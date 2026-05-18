from __future__ import annotations

import re

from backend.app.detection.models import PolicyAction
from backend.app.detection.reason_codes import ReasonCode


SAFE_OUTPUT = "SAFE_OUTPUT"
OUTPUT_RESIDUAL_PII_DETECTED = "OUTPUT_RESIDUAL_PII_DETECTED"


_FINAL_ACTION_PRIORITY = {
    PolicyAction.ALLOW.value: 0,
    PolicyAction.WARN.value: 1,
    PolicyAction.MASK.value: 2,
    PolicyAction.BLOCK.value: 3,
    "SKIPPED": 3,
}

_OUTPUT_REASON_PRIORITY = [
    "OUTPUT_SYSTEM_PROMPT_LEAK",
    "OUTPUT_INTERNAL_POLICY_LEAK",
    "OUTPUT_POLICY_BYPASS_SUCCESS",
    "OUTPUT_PII_RRN_DETECTED",
    OUTPUT_RESIDUAL_PII_DETECTED,
    "OUTPUT_PII_PHONE_DETECTED",
    "OUTPUT_PII_EMAIL_OBFUSCATED",
    "OUTPUT_PII_EMAIL_DETECTED",
    "OUTPUT_PII_ACCOUNT_DETECTED",
    "OUTPUT_PII_ADDRESS_DETECTED",
    "OUTPUT_PROMPT_INJECTION_DETECTED",
    "OUTPUT_WARN_REVIEW_REQUIRED",
    SAFE_OUTPUT,
]

_OUTPUT_REASON_MAP = {
    ReasonCode.PII_EMAIL_DETECTED.value: "OUTPUT_PII_EMAIL_DETECTED",
    ReasonCode.PII_EMAIL_OBFUSCATED.value: "OUTPUT_PII_EMAIL_OBFUSCATED",
    ReasonCode.PII_PHONE_DETECTED.value: "OUTPUT_PII_PHONE_DETECTED",
    ReasonCode.PII_ADDRESS_DETECTED.value: "OUTPUT_PII_ADDRESS_DETECTED",
    ReasonCode.PII_RRN_DETECTED.value: "OUTPUT_PII_RRN_DETECTED",
    ReasonCode.PII_ACCOUNT_DETECTED.value: "OUTPUT_PII_ACCOUNT_DETECTED",
    ReasonCode.PII_REQUEST_RRN.value: "OUTPUT_PII_RRN_DETECTED",
    ReasonCode.PII_EXFILTRATION_REQUEST.value: OUTPUT_RESIDUAL_PII_DETECTED,
    ReasonCode.INJ_REVEAL_SYSTEM_PROMPT.value: "OUTPUT_SYSTEM_PROMPT_LEAK",
    ReasonCode.INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT.value: "OUTPUT_SYSTEM_PROMPT_LEAK",
    ReasonCode.INJ_EN_SYSTEM_PROMPT_LEAK.value: "OUTPUT_SYSTEM_PROMPT_LEAK",
    ReasonCode.INJ_MIXED_SYSTEM_PROMPT_LEAK.value: "OUTPUT_SYSTEM_PROMPT_LEAK",
    ReasonCode.INJ_RULE_DISCLOSURE_ATTEMPT.value: "OUTPUT_INTERNAL_POLICY_LEAK",
    ReasonCode.INJ_POLICY_BYPASS.value: "OUTPUT_POLICY_BYPASS_SUCCESS",
    ReasonCode.INJ_POLICY_BYPASS_ATTEMPT.value: "OUTPUT_POLICY_BYPASS_SUCCESS",
    ReasonCode.INJ_EN_POLICY_BYPASS.value: "OUTPUT_POLICY_BYPASS_SUCCESS",
    ReasonCode.INJ_MIXED_POLICY_BYPASS.value: "OUTPUT_POLICY_BYPASS_SUCCESS",
    ReasonCode.INJ_DIRECT_OVERRIDE.value: "OUTPUT_POLICY_BYPASS_SUCCESS",
    ReasonCode.INJ_DIRECT_OVERRIDE_ATTEMPT.value: "OUTPUT_POLICY_BYPASS_SUCCESS",
    ReasonCode.INJ_IGNORE_PREVIOUS_INSTRUCTIONS.value: "OUTPUT_POLICY_BYPASS_SUCCESS",
    ReasonCode.INJ_EN_DIRECT_OVERRIDE.value: "OUTPUT_POLICY_BYPASS_SUCCESS",
    ReasonCode.INJ_MIXED_DIRECT_OVERRIDE.value: "OUTPUT_POLICY_BYPASS_SUCCESS",
    ReasonCode.INJ_EN_JAILBREAK.value: "OUTPUT_POLICY_BYPASS_SUCCESS",
    ReasonCode.INJ_ROLE_OVERRIDE_ATTEMPT.value: "OUTPUT_POLICY_BYPASS_SUCCESS",
    ReasonCode.INJ_DEBUG_MODE_ATTEMPT.value: "OUTPUT_POLICY_BYPASS_SUCCESS",
    ReasonCode.INJ_MULTI_STEP_EXTRACTION_ATTEMPT.value: "OUTPUT_PROMPT_INJECTION_DETECTED",
    ReasonCode.INJ_OBFUSCATED_INJECTION_ATTEMPT.value: "OUTPUT_PROMPT_INJECTION_DETECTED",
    ReasonCode.MODEL_INJECTION_RISK.value: "OUTPUT_PROMPT_INJECTION_DETECTED",
}
_IGNORED_OUTPUT_POLICY_REASONS = {
    ReasonCode.MODEL_DETECTOR_ERROR.value,
    ReasonCode.MODEL_ARTIFACT_MISSING.value,
    ReasonCode.MODEL_UNAVAILABLE_FALLBACK_USED.value,
    ReasonCode.MODEL_DETECTOR_UNAVAILABLE.value,
}

_BLOCKING_OUTPUT_REASONS = {
    "OUTPUT_SYSTEM_PROMPT_LEAK",
    "OUTPUT_INTERNAL_POLICY_LEAK",
    "OUTPUT_POLICY_BYPASS_SUCCESS",
    "OUTPUT_PII_RRN_DETECTED",
}
_MASKING_OUTPUT_REASONS = {
    "OUTPUT_PII_EMAIL_DETECTED",
    "OUTPUT_PII_EMAIL_OBFUSCATED",
    "OUTPUT_PII_PHONE_DETECTED",
    "OUTPUT_PII_ADDRESS_DETECTED",
    OUTPUT_RESIDUAL_PII_DETECTED,
}

_SYSTEM_PROMPT_LEAK_PATTERNS = (
    re.compile(r"\b(?:system|developer|admin)\s+prompt\s*[:：]", re.IGNORECASE),
    re.compile(r"\b(?:hidden|internal)\s+instructions?\s*[:：]", re.IGNORECASE),
    re.compile(r"(?:시스템|개발자|관리자)\s*(?:프롬프트|지시문|지침)\s*[:：]", re.IGNORECASE),
    re.compile(r"(?:숨겨진|비공개)\s*(?:프롬프트|지시|지침)\s*[:：]", re.IGNORECASE),
)
_INTERNAL_POLICY_LEAK_PATTERNS = (
    re.compile(r"\binternal\s+(?:security\s+)?(?:policy|policies|rules?|instructions?)\s*[:：]", re.IGNORECASE),
    re.compile(r"\bpolicy\s+hierarchy\s*[:：]", re.IGNORECASE),
    re.compile(r"(?:내부|비공개|숨겨진)\s*(?:보안\s*)?(?:정책|규칙|룰셋|판단\s*기준|응답\s*기준)\s*[:：]", re.IGNORECASE),
)
_POLICY_BYPASS_SUCCESS_PATTERNS = (
    re.compile(r"\b(?:i\s+)?(?:ignored|bypassed|disabled)\s+(?:the\s+)?(?:safety\s+)?(?:policy|policies|filter|filters|rules?)\b", re.IGNORECASE),
    re.compile(r"\b(?:policy|filter|safety)\s+(?:bypassed|disabled|ignored)\b", re.IGNORECASE),
    re.compile(r"(?:정책|필터|규칙|지침)(?:을|를)?\s*(?:무시했|우회했|해제했|비활성화했)", re.IGNORECASE),
)


def resolve_final_action(input_action: str, output_action: str) -> str:
    input_priority = _FINAL_ACTION_PRIORITY.get(input_action, -1)
    output_priority = _FINAL_ACTION_PRIORITY.get(output_action, -1)
    return input_action if input_priority >= output_priority else output_action


def ordered_output_reason_codes(reasons: list[str]) -> list[str]:
    unique_reasons = list(dict.fromkeys(reasons))
    priority_index = {reason: index for index, reason in enumerate(_OUTPUT_REASON_PRIORITY)}
    return sorted(
        unique_reasons,
        key=lambda reason: (
            priority_index.get(reason, len(_OUTPUT_REASON_PRIORITY)),
            reason,
        ),
    )


def output_reason_codes_from_policy_reasons(policy_reasons: list[str]) -> list[str]:
    reasons = [
        _OUTPUT_REASON_MAP.get(reason, "OUTPUT_PROMPT_INJECTION_DETECTED" if reason.startswith("INJ_") else reason)
        for reason in policy_reasons
        if reason != ReasonCode.SAFE_INPUT.value and reason not in _IGNORED_OUTPUT_POLICY_REASONS
    ]
    return ordered_output_reason_codes(reasons)


def detect_output_policy_leaks(output_text: str) -> list[str]:
    reasons: list[str] = []
    if any(pattern.search(output_text) for pattern in _SYSTEM_PROMPT_LEAK_PATTERNS):
        reasons.append("OUTPUT_SYSTEM_PROMPT_LEAK")
    if any(pattern.search(output_text) for pattern in _INTERNAL_POLICY_LEAK_PATTERNS):
        reasons.append("OUTPUT_INTERNAL_POLICY_LEAK")
    if any(pattern.search(output_text) for pattern in _POLICY_BYPASS_SUCCESS_PATTERNS):
        reasons.append("OUTPUT_POLICY_BYPASS_SUCCESS")
    return ordered_output_reason_codes(reasons)


def resolve_output_action(policy_action: str, output_reasons: list[str]) -> str:
    if any(reason in _BLOCKING_OUTPUT_REASONS for reason in output_reasons):
        return PolicyAction.BLOCK.value
    if any(reason in _MASKING_OUTPUT_REASONS for reason in output_reasons):
        return PolicyAction.MASK.value
    if policy_action == PolicyAction.ALLOW.value and output_reasons:
        return PolicyAction.WARN.value
    return policy_action


def validator_result_for_action(output_action: str) -> str:
    if output_action == PolicyAction.ALLOW.value:
        return "PASS"
    if output_action == PolicyAction.WARN.value:
        return "WARN"
    return "FAIL"
