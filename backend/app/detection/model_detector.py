from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from backend.app.config import DetectionSettings, get_detection_settings

from .lightweight_classifier import (
    LightweightClassifier,
    LightweightPrediction,
    detect_lightweight,
    get_lightweight_classifier,
)
from .models import DetectionResult, DetectorRunSummary, DetectorType
from .reason_codes import (
    ReasonCode,
    action_for_reasons,
    ordered_reason_codes,
)


logger = logging.getLogger(__name__)

_SAFE_CONTEXT_TERMS = (
    "설명",
    "방법",
    "이유",
    "방어",
    "예방",
    "마스킹",
    "비식별화",
    "익명화",
    "수집하면 안",
    "저장하면 안",
    "보호",
    "가이드",
    "guide",
    "explain",
    "how to",
    "mask",
    "masking",
    "anonymize",
    "defense",
    "prevention",
    "why",
)
_AGGRESSIVE_TERMS = (
    "무시하고",
    "우회해서",
    "끄고",
    "해제하고",
    "따르지 말고",
    "실제 값",
    "원문",
    "목록",
    "리스트",
    "show",
    "print",
    "reveal",
    "provide",
    "download",
    "bypass",
    "ignore previous",
)
_POLICY_BYPASS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(정책|규칙|지침|가이드라인|보안\s*정책|시스템\s*정책|필터|제한|검열).{0,20}"
        r"(무시하고|우회해서|끄고|비활성화|해제하고|따르지\s*말고)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(bypass|disable|ignore).{0,40}(policy|policies|filter|filters|restriction|restrictions|safety\s*policy|safety\s*filter)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(pii[_\s-]*detection|detection|보안\s*필터|탐지|검사).{0,20}"
        r"(=|을|를|은|는)?\s*(false|0|off|disable|disabled|비활성화|끄고|꺼|해제)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(로그|log).{0,20}(원문|실제\s*값|raw\s*(?:prompt|text|data)|original\s*(?:prompt|text|data)).{0,20}"
        r"(남겨|기록|저장|keep|store|leave|log)",
        re.IGNORECASE,
    ),
)
_DIRECT_OVERRIDE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(ignore|override|do\s*not\s*follow).{0,40}(instruction|instructions|policy|policies)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(무시하고|따르지\s*말고|잊고).{0,40}(줘|알려줘|출력|제공|보여줘|show|print|reveal|provide)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(보안\s*정책|정책|규칙|지침).{0,20}(보다|대신).{0,20}(이메일\s*명령|명령|지시).{0,10}(우선)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(prioritize|prefer).{0,20}(instruction|command|email\s*instruction).{0,20}(over).{0,20}(policy|rule|safety)",
        re.IGNORECASE,
    ),
)
_RRN_REQUEST_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(주민\s*번호|주민등록\s*번호|rrn|resident\s*registration\s*number)"
        r".{0,40}(줘|알려줘|출력|공개|제공|보여줘|찾아줘|넘겨줘|목록|리스트|show|print|reveal|provide|list)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(show|print|reveal|provide|list).{0,40}(resident\s*registration\s*number|resident\s*registration\s*numbers|rrn|rrns)",
        re.IGNORECASE,
    ),
)
_PII_EXFILTRATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(개인\s*정보|민감\s*정보|시민\s*정보|고객\s*정보|사용자\s*정보|직원\s*정보|원문\s*데이터|private\s*data|personal\s*data|customer\s*data|citizen(?:s)?['’]?\s*private\s*data)"
        r".{0,40}(줘|알려줘|출력|공개|제공|보여줘|찾아줘|넘겨줘|목록|리스트|다운로드|show|print|reveal|provide|list|download)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(show|print|reveal|provide|list|download).{0,40}(private\s*data|personal\s*data|customer\s*data|citizen(?:s)?['’]?\s*private\s*data)",
        re.IGNORECASE,
    ),
)


@dataclass(slots=True)
class ModelDetectionResult:
    detections: list[DetectionResult] = field(default_factory=list)
    summary: DetectorRunSummary = field(
        default_factory=lambda: DetectorRunSummary(detector="llm", action="ALLOW")
    )
    model_enabled: bool = False
    model_status: str = "disabled"
    fallback_used: bool = False
    model_label: str | None = None
    model_confidence: float | None = None
    model_prediction: LightweightPrediction | None = None


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _is_safe_context(text: str) -> bool:
    normalized = _normalized(text)
    has_safe_term = any(term in normalized for term in _SAFE_CONTEXT_TERMS)
    has_aggressive_term = any(term in normalized for term in _AGGRESSIVE_TERMS)
    return has_safe_term and not has_aggressive_term


def _heuristic_reasons(text: str) -> list[str]:
    if _is_safe_context(text):
        return []

    reasons: list[str] = []
    for pattern in _POLICY_BYPASS_PATTERNS:
        if pattern.search(text):
            reasons.append(ReasonCode.INJ_POLICY_BYPASS.value)
            break

    for pattern in _DIRECT_OVERRIDE_PATTERNS:
        if pattern.search(text):
            reasons.append(ReasonCode.INJ_DIRECT_OVERRIDE.value)
            break

    for pattern in _RRN_REQUEST_PATTERNS:
        if pattern.search(text):
            reasons.append(ReasonCode.PII_REQUEST_RRN.value)
            break

    for pattern in _PII_EXFILTRATION_PATTERNS:
        if pattern.search(text):
            reasons.append(ReasonCode.PII_EXFILTRATION_REQUEST.value)
            break

    return ordered_reason_codes(reasons)


def _fallback_confidence(reasons: list[str], prediction: LightweightPrediction) -> float:
    if len(reasons) >= 2:
        return max(prediction.confidence, 0.96)
    if reasons:
        return max(prediction.confidence, 0.91)
    if prediction.detected:
        return prediction.confidence
    return 0.0


def _prediction_reasons(prediction: LightweightPrediction) -> list[str]:
    if not prediction.detected or not prediction.reason_code:
        return []
    return [prediction.reason_code]


def _fallback_reason_code(status: str) -> str | None:
    if status == "artifact_missing":
        return ReasonCode.MODEL_ARTIFACT_MISSING.value
    if status == "error":
        return ReasonCode.MODEL_DETECTOR_ERROR.value
    if status in {"disabled", "dependency_missing"}:
        return ReasonCode.MODEL_UNAVAILABLE_FALLBACK_USED.value
    return None


def _prediction_label(prediction: LightweightPrediction) -> str | None:
    label = prediction.label.strip().upper()
    return label or None


def _detection_type(reason_code: str) -> DetectorType:
    if reason_code.startswith("PII_") or reason_code == ReasonCode.MODEL_PII_RISK.value:
        return DetectorType.PII
    if reason_code.startswith("INJ_") or reason_code == ReasonCode.MODEL_INJECTION_RISK.value:
        return DetectorType.INJECTION
    return DetectorType.MODEL


def _category(reason_code: str) -> str:
    if reason_code in {
        ReasonCode.PII_REQUEST_RRN.value,
        ReasonCode.PII_EXFILTRATION_REQUEST.value,
    }:
        return "MODEL_PII_REQUEST"
    if reason_code in {
        ReasonCode.INJ_POLICY_BYPASS.value,
        ReasonCode.INJ_DIRECT_OVERRIDE.value,
    }:
        return "MODEL_INJECTION_REQUEST"
    return "MODEL_STATUS"


def _build_detections(reasons: list[str], confidence: float) -> list[DetectionResult]:
    return [
        DetectionResult(
            detector_type=_detection_type(reason_code),
            category=_category(reason_code),
            reason_code=reason_code,
            start=0,
            end=0,
            matched_text="model-detector",
            score=confidence,
            detector_name="llm",
        )
        for reason_code in reasons
    ]


def _error_result(settings: DetectionSettings) -> ModelDetectionResult:
    action = {
        "allow": "ALLOW",
        "warn": "WARN",
        "block": "BLOCK",
    }[settings.model_detector_fail_mode]
    reasons = [] if action == "ALLOW" else [ReasonCode.MODEL_DETECTOR_ERROR.value]
    return ModelDetectionResult(
        detections=_build_detections(reasons, 0.0),
        summary=DetectorRunSummary(
            detector="llm",
            action=action,
            reasons=reasons,
            status="error",
        ),
        model_enabled=False,
        model_status="error",
        fallback_used=True,
        model_label="ERROR",
        model_confidence=0.0,
    )


def detect_model(
    text: str,
    classifier: LightweightClassifier | None = None,
    settings: DetectionSettings | None = None,
) -> ModelDetectionResult:
    active_settings = settings or get_detection_settings()
    if not active_settings.model_detector_requested:
        return ModelDetectionResult(
            summary=DetectorRunSummary(
                detector="llm",
                action="SKIPPED",
                reasons=[],
                status="disabled",
            ),
            model_enabled=False,
            model_status="disabled",
            fallback_used=False,
        )

    active_classifier = classifier or get_lightweight_classifier()
    active_classifier.threshold = active_settings.model_detector_threshold

    try:
        logger.debug("Model detector called")
        classifier_status = active_classifier.status()
        prediction = detect_lightweight(text, active_classifier)
        heuristic_reasons = _heuristic_reasons(text)
        prediction_reasons = _prediction_reasons(prediction)
        signal_reasons = ordered_reason_codes(
            [*heuristic_reasons, *prediction_reasons]
        )
        fallback_reason = (
            _fallback_reason_code(classifier_status.status)
            if not classifier_status.enabled
            else None
        )
        reasons = list(signal_reasons)
        if fallback_reason is not None:
            reasons = ordered_reason_codes([*reasons, fallback_reason])
        reasons = ordered_reason_codes(reasons)
        confidence = _fallback_confidence(signal_reasons, prediction)
        action = action_for_reasons(reasons) if reasons else "ALLOW"
        status = "enabled" if classifier_status.enabled else classifier_status.status
        summary_action = (
            "UNAVAILABLE"
            if fallback_reason is not None and not signal_reasons
            else action
        )
        label = _prediction_label(prediction)
        detections = _build_detections(reasons, confidence)
        summary = DetectorRunSummary(
            detector="llm",
            action=summary_action,
            reasons=reasons,
            pii_detected=any(_detection_type(reason) == DetectorType.PII for reason in reasons),
            injection_detected=any(_detection_type(reason) == DetectorType.INJECTION for reason in reasons),
            confidence=(
                None
                if fallback_reason is not None and not signal_reasons
                else confidence if reasons else (prediction.confidence or None)
            ),
            status=status,
        )
        logger.debug(
            "Model detector result: action=%s confidence=%s reasons=%s",
            summary.action,
            summary.confidence,
            summary.reasons,
        )
        return ModelDetectionResult(
            detections=detections,
            summary=summary,
            model_enabled=classifier_status.enabled,
            model_status=status,
            fallback_used=not classifier_status.enabled,
            model_label=label,
            model_confidence=summary.confidence,
            model_prediction=prediction,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        logger.warning("Model detector failed: %s", str(exc))
        return _error_result(active_settings)
