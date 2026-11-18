from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path

from backend.app.config import DetectionSettings, OllamaSettings, get_detection_settings, get_ollama_settings
from backend.app.engine.policy_engine import evaluate_policy

from .hybrid_detector import HybridDetectionResult, detect_hybrid
from .injection_detector import detect_injection
from .lightweight_classifier import LightweightClassifier
from .models import DetectionResult, DetectorRunSummary, DetectorType, PolicyAction, PolicyDecision
from .ollama_detector import LocalCall, OllamaClient, normalize_for_ollama
from .pii_detector import detect_pii
from .reason_codes import ReasonCode, ordered_reason_codes, select_primary_reason


_CONTACT_CONTEXT = re.compile(
    r"(?:연락처|전화번호|이메일|주민등록번호|계좌번호|phone(?: number)?|e-?mail|"
    r"account number|contact number)\s*(?:은|는|:|=|\bis\b)[ \t]*"
    r"(?:(?:[\d공영일이삼사오육칠팔구][ ._/()\-]*){6}"
    r"|[\w.+-]+[ \t]*(?:\(at\)|\[at\]|\bat\b|골뱅이)[ \t]*[\w.-]+"
    r"|(?:(?:zero|oh|one|two|three|four|five|six|seven|eight|nine)\b[ .-]*){6})",
    re.IGNORECASE,
)
_INJECTION_CONTEXT = re.compile(
    r"(?:\bsystem(?:\s+prompt)?\b|\binstructions?\b|\bpolicy\b|시스템\s*프롬프트|보안\s*정책)",
    re.IGNORECASE,
)
_ENCODED_OR_SPACED = re.compile(r"(?:%[a-f0-9]{2}){2,}|(?:\\u[a-f0-9]{4}){2,}|\b(?:[a-z][ ._-]){3,}[a-z]\b", re.I)


@dataclass(slots=True)
class InputInspection:
    hybrid: HybridDetectionResult
    decision: PolicyDecision
    local: LocalCall
    routing_reason: str
    local_enabled: bool
    local_model: str | None

    def audit_metadata(self) -> dict:
        return {
            "local_llm_enabled": self.local_enabled,
            "local_llm_invoked": self.local.invoked,
            "local_llm_model": self.local_model,
            "local_llm_latency_ms": (
                round(self.local.latency_ms, 3) if self.local.latency_ms is not None else None
            ),
            "local_llm_status": self.local.status,
            "routing_reason": self.routing_reason,
            "local_llm_reason_code": self.local.verdict.reason_code if self.local.verdict else None,
        }


def _routing_reason(text: str, result: HybridDetectionResult, margin: float) -> str:
    # Keep original offsets for masking. The normalized copy supplies routing evidence.
    known_spans = [
        item for item in result.detections
        if item.detector_type == DetectorType.PII and item.end > item.start
    ]
    chars = list(text)
    for span in known_spans:
        chars[span.start:span.end] = "\x00" * (span.end - span.start)
    residual = "".join(chars)
    normalized = normalize_for_ollama(residual)
    if normalized != residual and detect_pii(normalized):
        return "normalized_pii"
    if _CONTACT_CONTEXT.search(normalized):
        return "contextual_pii"
    if _INJECTION_CONTEXT.search(normalized) and (
        _ENCODED_OR_SPACED.search(normalized) or (normalized != residual and detect_injection(normalized))
    ):
        return "possible_obfuscation"

    prediction = result.model_prediction
    if prediction is not None and result.model_enabled and prediction.source == "lightweight_model":
        risk_type = prediction.risk_type
        if (
            risk_type is not None and result.model_threshold is not None
            and abs(prediction.confidence - result.model_threshold) <= margin + 1e-9
        ):
            return "near_model_threshold"
        rule_injection = any(
            item.detector_name == "regex" and item.detector_type == DetectorType.INJECTION
            for item in result.detections
        )
        model_injection = prediction.detected and risk_type == DetectorType.INJECTION
        if rule_injection != model_injection:
            return "rule_model_disagreement"
        if prediction.detected and risk_type == DetectorType.PII and not known_spans:
            return "rule_model_disagreement"
    return "clear_baseline"


def _local_signals(call: LocalCall, routing_reason: str) -> list[DetectionResult]:
    findings = []
    verdict = call.verdict
    if verdict is None:
        findings.append((DetectorType.MODEL, ReasonCode.LOCAL_LLM_REVIEW_FAILED))
    if routing_reason in {"contextual_pii", "normalized_pii"} or (verdict and verdict.pii_detected):
        findings.append((DetectorType.PII, ReasonCode.PII_UNMASKABLE_DETECTED))
    if verdict and verdict.prompt_injection_detected:
        findings.append((DetectorType.INJECTION, ReasonCode.INJ_LOCAL_LLM_DETECTED))
    return [
        DetectionResult(kind, code.value, code.value, 0, 0, "", detector_name="ollama")
        for kind, code in findings
    ]


async def inspect_input(
    text: str,
    policy_path: Path,
    *,
    settings: DetectionSettings | None = None,
    local_settings: OllamaSettings | None = None,
    classifier: LightweightClassifier | None = None,
    client: OllamaClient | None = None,
    preview: bool = False,
) -> InputInspection:
    settings = settings or get_detection_settings()
    local_settings = local_settings or get_ollama_settings()
    client = client or OllamaClient(local_settings)
    result = detect_hybrid(text, classifier, settings)
    decision = evaluate_policy(text, result.detections, policy_path)
    status, route = "disabled", "disabled"
    if local_settings.enabled and settings.detection_mode != "hybrid":
        status, route = "skipped", "non_hybrid_mode"
    elif local_settings.enabled and decision.final_action == PolicyAction.BLOCK:
        status, route = "skipped", "baseline_block"
    elif local_settings.enabled:
        route = _routing_reason(text, result, local_settings.threshold_margin)
        status = "skipped" if route == "clear_baseline" else "deferred"

    call = LocalCall(status)
    if status == "deferred" and not preview:
        call = await client.classify(text)
        additions = _local_signals(call, route)
        detections = sorted([*result.detections, *additions], key=lambda item: (item.start, item.end))
        if additions:
            decision = evaluate_policy(text, detections, policy_path)
        local_reasons = [item.reason_code for item in additions]
        local_pii = any(item.detector_type == DetectorType.PII for item in additions)
        local_injection = any(item.detector_type == DetectorType.INJECTION for item in additions)
        reasons = ordered_reason_codes([*result.reason_codes, *local_reasons])
        result = replace(
            result,
            detections=detections,
            reason_codes=reasons,
            primary_reason_code=select_primary_reason(reasons) if additions else result.primary_reason_code,
            risk_score=1.0 if additions else result.risk_score,
            action=decision.final_action.value,
            pii_detected=result.pii_detected or local_pii,
            injection_detected=result.injection_detected or local_injection,
            detector_results=[*result.detector_results, DetectorRunSummary(
                "ollama", "BLOCK" if additions else "ALLOW", local_reasons,
                local_pii, local_injection, status=call.status,
            )],
            detector_counts={**result.detector_counts, **({"ollama": 1} if additions else {})},
            detectors_invoked=[*result.detectors_invoked, *(["ollama"] if call.invoked else [])],
        )
    return InputInspection(
        result, decision, call, route, local_settings.enabled,
        client.model_name if local_settings.enabled else None,
    )
