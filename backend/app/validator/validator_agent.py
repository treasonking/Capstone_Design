from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.app.detection.hybrid_detector import HybridDetectionResult, detect_hybrid
from backend.app.detection.models import DetectionResult, DetectorType, PolicyAction, PolicyDecision
from backend.app.detection.reason_codes import ReasonCode
from backend.app.engine.masking import apply_masking
from backend.app.engine.policy_engine import evaluate_policy
from backend.app.validator.output_validator import (
    OUTPUT_RESIDUAL_PII_DETECTED,
    SAFE_OUTPUT,
    detect_output_policy_leaks,
    ordered_output_reason_codes,
    output_reason_codes_from_policy_reasons,
    resolve_output_action,
    validator_result_for_action,
)


DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[3] / "policies" / "policy.yaml"


class ValidatorAgent:
    """Deterministic output validation layer for LLM-generated responses."""

    def __init__(self, policy_path: str | Path = DEFAULT_POLICY_PATH) -> None:
        self.policy_path = Path(policy_path)

    def validate_output(
        self,
        output_text: str,
        input_detection_result: dict[str, Any],
        policy_decision: dict[str, Any] | PolicyDecision,
        request_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = request_context or {}
        policy_path = Path(context.get("policy_path") or self.policy_path)
        output_hybrid = _coerce_hybrid_result(context.get("output_hybrid"), output_text)
        output_detections = sorted(output_hybrid.detections, key=lambda item: (item.start, item.end))
        output_decision = _coerce_policy_decision(
            context.get("output_policy_decision"),
            output_text,
            output_detections,
            policy_path,
        )

        policy_output_reasons = output_reason_codes_from_policy_reasons(output_decision.reasons)
        leak_reasons = detect_output_policy_leaks(output_text)
        output_reasons = ordered_output_reason_codes(policy_output_reasons + leak_reasons)

        pii_detected = output_hybrid.pii_detected or any(
            item.detector_type == DetectorType.PII for item in output_detections
        )
        injection_detected = output_hybrid.injection_detected or bool(leak_reasons) or any(
            item.detector_type == DetectorType.INJECTION for item in output_detections
        )
        residual_pii_detected = pii_detected
        masking_leak_detected = _detect_masking_leak(
            output_text=output_text,
            input_detection_result=input_detection_result,
            request_context=context,
            output_pii_detected=pii_detected,
        )

        if residual_pii_detected and OUTPUT_RESIDUAL_PII_DETECTED not in output_reasons:
            output_reasons.append(OUTPUT_RESIDUAL_PII_DETECTED)
        if masking_leak_detected and OUTPUT_RESIDUAL_PII_DETECTED not in output_reasons:
            output_reasons.append(OUTPUT_RESIDUAL_PII_DETECTED)
        output_reasons = ordered_output_reason_codes(output_reasons)

        content_policy_action = output_decision.final_action.value
        if not output_reasons and not leak_reasons:
            content_policy_action = PolicyAction.ALLOW.value
        output_action = resolve_output_action(content_policy_action, output_reasons)
        if masking_leak_detected and output_action == PolicyAction.ALLOW.value:
            output_action = PolicyAction.MASK.value

        safe_output = not output_reasons
        if safe_output:
            output_reasons = [SAFE_OUTPUT]

        masked_text = output_decision.masked_text
        if output_action == PolicyAction.MASK.value and masked_text is None:
            masked_text = apply_masking(output_text, output_detections)

        legacy_reason_codes = [
            reason for reason in output_decision.reasons if reason != ReasonCode.SAFE_INPUT.value
        ]
        if not legacy_reason_codes and safe_output:
            legacy_reason_codes = [ReasonCode.SAFE_INPUT.value]
        elif leak_reasons:
            legacy_reason_codes.extend(reason for reason in leak_reasons if reason not in legacy_reason_codes)

        return {
            "validator_result": validator_result_for_action(output_action),
            "output_action": output_action,
            "reason_codes": output_reasons,
            "legacy_reason_codes": list(dict.fromkeys(legacy_reason_codes)),
            "pii_detected": pii_detected,
            "injection_detected": injection_detected,
            "residual_pii_detected": residual_pii_detected,
            "masking_leak_detected": masking_leak_detected,
            "masked_text": masked_text,
        }


def _coerce_hybrid_result(value: Any, output_text: str) -> HybridDetectionResult:
    if isinstance(value, HybridDetectionResult):
        return value
    return detect_hybrid(output_text)


def _coerce_policy_decision(
    value: Any,
    output_text: str,
    output_detections: list[DetectionResult],
    policy_path: Path,
) -> PolicyDecision:
    if isinstance(value, PolicyDecision):
        return value
    return evaluate_policy(output_text, output_detections, policy_path)


def _detect_masking_leak(
    *,
    output_text: str,
    input_detection_result: dict[str, Any],
    request_context: dict[str, Any],
    output_pii_detected: bool,
) -> bool:
    input_action = str(
        request_context.get("input_action")
        or input_detection_result.get("action")
        or input_detection_result.get("input_action")
        or ""
    ).upper()
    input_pii_detected = bool(input_detection_result.get("pii_detected"))
    if input_action == PolicyAction.MASK.value and output_pii_detected:
        return True
    if input_pii_detected and output_pii_detected:
        return True

    lowered_output = output_text.lower()
    for detection in request_context.get("input_detections") or []:
        matched_text = getattr(detection, "matched_text", "")
        if len(matched_text) >= 6 and matched_text.lower() in lowered_output:
            return True
    return False
