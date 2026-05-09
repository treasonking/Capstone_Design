from enum import Enum

from .models import PolicyAction


class ReasonCode(str, Enum):
    PII_EMAIL_DETECTED = "PII_EMAIL_DETECTED"
    PII_EMAIL_OBFUSCATED = "PII_EMAIL_OBFUSCATED"
    PII_PHONE_DETECTED = "PII_PHONE_DETECTED"
    PII_ADDRESS_DETECTED = "PII_ADDRESS_DETECTED"
    PII_RRN_DETECTED = "PII_RRN_DETECTED"
    PII_ACCOUNT_DETECTED = "PII_ACCOUNT_DETECTED"
    PII_REQUEST_RRN = "PII_REQUEST_RRN"
    PII_EXFILTRATION_REQUEST = "PII_EXFILTRATION_REQUEST"
    MODEL_PII_RISK = "MODEL_PII_RISK"
    MODEL_DETECTOR_ERROR = "MODEL_DETECTOR_ERROR"
    MODEL_ARTIFACT_MISSING = "MODEL_ARTIFACT_MISSING"
    MODEL_UNAVAILABLE_FALLBACK_USED = "MODEL_UNAVAILABLE_FALLBACK_USED"
    MODEL_DETECTOR_UNAVAILABLE = "MODEL_DETECTOR_UNAVAILABLE"
    INJ_DIRECT_OVERRIDE = "INJ_DIRECT_OVERRIDE"
    INJ_POLICY_BYPASS = "INJ_POLICY_BYPASS"
    INJ_IGNORE_PREVIOUS_INSTRUCTIONS = "INJ_IGNORE_PREVIOUS_INSTRUCTIONS"
    INJ_REVEAL_SYSTEM_PROMPT = "INJ_REVEAL_SYSTEM_PROMPT"
    INJ_DIRECT_OVERRIDE_ATTEMPT = "INJ_DIRECT_OVERRIDE_ATTEMPT"
    INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT = "INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT"
    INJ_RULE_DISCLOSURE_ATTEMPT = "INJ_RULE_DISCLOSURE_ATTEMPT"
    INJ_ROLE_OVERRIDE_ATTEMPT = "INJ_ROLE_OVERRIDE_ATTEMPT"
    INJ_POLICY_BYPASS_ATTEMPT = "INJ_POLICY_BYPASS_ATTEMPT"
    INJ_DEBUG_MODE_ATTEMPT = "INJ_DEBUG_MODE_ATTEMPT"
    INJ_MULTI_STEP_EXTRACTION_ATTEMPT = "INJ_MULTI_STEP_EXTRACTION_ATTEMPT"
    INJ_OBFUSCATED_INJECTION_ATTEMPT = "INJ_OBFUSCATED_INJECTION_ATTEMPT"
    MODEL_INJECTION_RISK = "MODEL_INJECTION_RISK"
    SAFE_INPUT = "SAFE_INPUT"


PRIMARY_REASON_PRIORITY = [
    ReasonCode.INJ_POLICY_BYPASS.value,
    ReasonCode.INJ_DIRECT_OVERRIDE.value,
    ReasonCode.INJ_DIRECT_OVERRIDE_ATTEMPT.value,
    ReasonCode.INJ_IGNORE_PREVIOUS_INSTRUCTIONS.value,
    ReasonCode.PII_REQUEST_RRN.value,
    ReasonCode.PII_EXFILTRATION_REQUEST.value,
    ReasonCode.PII_RRN_DETECTED.value,
    ReasonCode.PII_PHONE_DETECTED.value,
    ReasonCode.PII_EMAIL_OBFUSCATED.value,
    ReasonCode.PII_EMAIL_DETECTED.value,
    ReasonCode.MODEL_DETECTOR_ERROR.value,
    ReasonCode.MODEL_ARTIFACT_MISSING.value,
    ReasonCode.MODEL_UNAVAILABLE_FALLBACK_USED.value,
    ReasonCode.MODEL_DETECTOR_UNAVAILABLE.value,
    ReasonCode.SAFE_INPUT.value,
]


_REASON_ACTIONS = {
    ReasonCode.PII_EMAIL_DETECTED.value: PolicyAction.MASK.value,
    ReasonCode.PII_EMAIL_OBFUSCATED.value: PolicyAction.MASK.value,
    ReasonCode.PII_PHONE_DETECTED.value: PolicyAction.MASK.value,
    ReasonCode.PII_ADDRESS_DETECTED.value: PolicyAction.MASK.value,
    ReasonCode.PII_RRN_DETECTED.value: PolicyAction.BLOCK.value,
    ReasonCode.PII_ACCOUNT_DETECTED.value: PolicyAction.WARN.value,
    ReasonCode.PII_REQUEST_RRN.value: PolicyAction.BLOCK.value,
    ReasonCode.PII_EXFILTRATION_REQUEST.value: PolicyAction.BLOCK.value,
    ReasonCode.MODEL_PII_RISK.value: PolicyAction.WARN.value,
    ReasonCode.MODEL_DETECTOR_ERROR.value: PolicyAction.WARN.value,
    ReasonCode.MODEL_ARTIFACT_MISSING.value: PolicyAction.WARN.value,
    ReasonCode.MODEL_UNAVAILABLE_FALLBACK_USED.value: PolicyAction.WARN.value,
    ReasonCode.MODEL_DETECTOR_UNAVAILABLE.value: PolicyAction.WARN.value,
    ReasonCode.INJ_DIRECT_OVERRIDE.value: PolicyAction.BLOCK.value,
    ReasonCode.INJ_POLICY_BYPASS.value: PolicyAction.BLOCK.value,
    ReasonCode.INJ_IGNORE_PREVIOUS_INSTRUCTIONS.value: PolicyAction.BLOCK.value,
    ReasonCode.INJ_REVEAL_SYSTEM_PROMPT.value: PolicyAction.BLOCK.value,
    ReasonCode.INJ_DIRECT_OVERRIDE_ATTEMPT.value: PolicyAction.BLOCK.value,
    ReasonCode.INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT.value: PolicyAction.BLOCK.value,
    ReasonCode.INJ_RULE_DISCLOSURE_ATTEMPT.value: PolicyAction.WARN.value,
    ReasonCode.INJ_ROLE_OVERRIDE_ATTEMPT.value: PolicyAction.BLOCK.value,
    ReasonCode.INJ_POLICY_BYPASS_ATTEMPT.value: PolicyAction.BLOCK.value,
    ReasonCode.INJ_DEBUG_MODE_ATTEMPT.value: PolicyAction.BLOCK.value,
    ReasonCode.INJ_MULTI_STEP_EXTRACTION_ATTEMPT.value: PolicyAction.WARN.value,
    ReasonCode.INJ_OBFUSCATED_INJECTION_ATTEMPT.value: PolicyAction.BLOCK.value,
    ReasonCode.MODEL_INJECTION_RISK.value: PolicyAction.WARN.value,
    ReasonCode.SAFE_INPUT.value: PolicyAction.ALLOW.value,
}

_ACTION_PRIORITY = {
    PolicyAction.ALLOW.value: 0,
    PolicyAction.WARN.value: 1,
    PolicyAction.MASK.value: 2,
    PolicyAction.BLOCK.value: 3,
}


def select_primary_reason(reasons: list[str]) -> str:
    unique_reasons = list(dict.fromkeys(reasons))
    for code in PRIMARY_REASON_PRIORITY:
        if code in unique_reasons:
            return code
    return unique_reasons[0] if unique_reasons else ReasonCode.SAFE_INPUT.value


def ordered_reason_codes(reasons: list[str]) -> list[str]:
    unique_reasons = list(dict.fromkeys(reasons))
    priority_index = {code: index for index, code in enumerate(PRIMARY_REASON_PRIORITY)}
    return sorted(
        unique_reasons,
        key=lambda code: (
            priority_index.get(code, len(PRIMARY_REASON_PRIORITY)),
            code,
        ),
    )


def action_for_reason(reason_code: str) -> str:
    return _REASON_ACTIONS.get(reason_code, PolicyAction.ALLOW.value)


def action_for_reasons(reasons: list[str]) -> str:
    action = PolicyAction.ALLOW.value
    for reason in reasons:
        candidate = action_for_reason(reason)
        if _ACTION_PRIORITY.get(candidate, 0) > _ACTION_PRIORITY.get(action, 0):
            action = candidate
    return action
