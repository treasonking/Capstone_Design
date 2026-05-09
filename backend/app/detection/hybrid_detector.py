from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend.app.config import DetectionSettings, get_detection_settings

from .injection_detector import detect_injection
from .lightweight_classifier import (
    LightweightClassifier,
    LightweightPrediction,
    get_lightweight_classifier,
)
from .model_detector import detect_model
from .models import DetectionResult, DetectorRunSummary
from .pii_detector import detect_pii
from .reason_codes import action_for_reasons, ordered_reason_codes, select_primary_reason


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class HybridDetectionResult:
    detections: list[DetectionResult]
    model_enabled: bool
    model_status: str
    fallback_used: bool
    model_label: str | None = None
    model_confidence: float | None = None
    model_threshold: float | None = None
    model_prediction_accepted: bool = False
    model_reason_code: str | None = None
    reason_codes: list[str] = field(default_factory=list)
    primary_reason_code: str | None = None
    risk_score: float = 0.0
    model_prediction: LightweightPrediction | None = None
    detector_results: list[DetectorRunSummary] = field(default_factory=list)
    detector_counts: dict[str, int] = field(default_factory=dict)
    detectors_invoked: list[str] = field(default_factory=list)
    action: str = "ALLOW"
    pii_detected: bool = False
    injection_detected: bool = False

    @property
    def classifier_enabled(self) -> bool:
        return self.model_enabled


HybridDetectionSummary = HybridDetectionResult


def _normalized_score(detection: DetectionResult) -> float:
    return min(detection.score, 1.0)


def _priority_key(detection: DetectionResult) -> tuple[float, str, str]:
    source_bias = "0" if detection.detector_name == "llm" else "1"
    return (
        _normalized_score(detection),
        source_bias,
        detection.reason_code,
    )


def _dedupe(detections: list[DetectionResult]) -> list[DetectionResult]:
    deduped: list[DetectionResult] = []
    seen: set[tuple[str, str, int, int, str, str]] = set()

    for item in detections:
        key = (
            item.detector_type.value,
            item.reason_code,
            item.start,
            item.end,
            item.matched_text,
            item.detector_name,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped


def _regex_summary(detections: list[DetectionResult], requested: bool) -> DetectorRunSummary:
    if not requested:
        return DetectorRunSummary(detector="regex", action="SKIPPED", status="disabled")

    reasons = ordered_reason_codes([item.reason_code for item in detections])
    return DetectorRunSummary(
        detector="regex",
        action=action_for_reasons(reasons) if reasons else "ALLOW",
        reasons=reasons,
        pii_detected=any(item.detector_type.value == "PII" for item in detections),
        injection_detected=any(item.detector_type.value == "INJECTION" for item in detections),
        status="completed",
    )


def _detector_counts(detector_results: list[DetectorRunSummary]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in detector_results:
        if not result.reasons:
            continue
        counts[result.detector] = counts.get(result.detector, 0) + 1
    return counts


def detect_hybrid(
    text: str,
    classifier: LightweightClassifier | None = None,
    settings: DetectionSettings | None = None,
) -> HybridDetectionResult:
    active_settings = settings or get_detection_settings()
    active_classifier = classifier or get_lightweight_classifier()

    regex_detections: list[DetectionResult] = []
    if active_settings.regex_detector_requested:
        regex_detections.extend(detect_pii(text))
        regex_detections.extend(detect_injection(text))
    regex_summary = _regex_summary(regex_detections, active_settings.regex_detector_requested)
    logger.debug(
        "Regex detector result: action=%s reasons=%s",
        regex_summary.action,
        regex_summary.reasons,
    )

    model_result = detect_model(text, active_classifier, active_settings)

    detector_results = [
        result
        for result in (regex_summary, model_result.summary)
        if result.action != "SKIPPED" or result.reasons
    ]
    combined = _dedupe(
        sorted(
            [*regex_detections, *model_result.detections],
            key=lambda item: (
                item.start,
                item.end,
                item.category,
                item.reason_code,
                item.detector_name,
            ),
        )
    )
    primary = max(combined, key=_priority_key) if combined else None
    reason_codes = ordered_reason_codes([item.reason_code for item in combined])
    final_action = action_for_reasons(reason_codes) if reason_codes else "ALLOW"
    detector_counts = _detector_counts(detector_results)
    detectors_invoked = [result.detector for result in detector_results]

    final_result = HybridDetectionResult(
        detections=combined,
        model_enabled=model_result.model_enabled,
        model_status=model_result.model_status,
        model_label=model_result.model_label,
        model_confidence=model_result.model_confidence,
        model_threshold=model_result.model_threshold,
        model_prediction_accepted=model_result.model_prediction_accepted,
        model_reason_code=model_result.model_reason_code,
        fallback_used=model_result.fallback_used,
        reason_codes=reason_codes,
        primary_reason_code=(
            select_primary_reason(reason_codes)
            if reason_codes
            else primary.reason_code if primary else None
        ),
        risk_score=max((_normalized_score(item) for item in combined), default=0.0),
        model_prediction=model_result.model_prediction,
        detector_results=detector_results,
        detector_counts=detector_counts,
        detectors_invoked=detectors_invoked,
        action=final_action,
        pii_detected=any(item.detector_type.value == "PII" for item in combined),
        injection_detected=any(item.detector_type.value == "INJECTION" for item in combined),
    )
    logger.info(
        "Final detection result: action=%s reasons=%s",
        final_result.action,
        final_result.reason_codes,
    )
    return final_result


def detect_hybrid_detections(
    text: str,
    classifier: LightweightClassifier | None = None,
    settings: DetectionSettings | None = None,
) -> list[DetectionResult]:
    return detect_hybrid(text, classifier, settings).detections
