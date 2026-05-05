from __future__ import annotations

from dataclasses import dataclass

from .injection_detector import detect_injection
from .lightweight_classifier import (
    LightweightClassifier,
    LightweightPrediction,
    detect_lightweight,
    get_lightweight_classifier,
    prediction_to_detection,
)
from .models import DetectionResult, DetectorType
from .pii_detector import detect_pii


@dataclass(slots=True)
class HybridDetectionSummary:
    detections: list[DetectionResult]
    reason_codes: list[str]
    primary_reason_code: str | None
    risk_score: float
    classifier_enabled: bool
    fallback_used: bool
    model_prediction: LightweightPrediction


def _normalized_score(detection: DetectionResult) -> float:
    if detection.detector_type == DetectorType.INJECTION:
        return min(detection.score / 5.0, 1.0)
    return min(detection.score, 1.0)


def _priority_key(detection: DetectionResult) -> tuple[float, int, str]:
    source_bias = 0 if detection.category.startswith("MODEL_") else 1
    return (
        _normalized_score(detection),
        source_bias,
        detection.reason_code,
    )


def _dedupe(detections: list[DetectionResult]) -> list[DetectionResult]:
    deduped: list[DetectionResult] = []
    seen: set[tuple[str, str, int, int, str]] = set()

    for item in detections:
        key = (
            item.detector_type.value,
            item.reason_code,
            item.start,
            item.end,
            item.matched_text,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped


def detect_hybrid(
    text: str,
    classifier: LightweightClassifier | None = None,
) -> HybridDetectionSummary:
    pii_detections = detect_pii(text)
    rule_detections = detect_injection(text)
    active_classifier = classifier or get_lightweight_classifier()
    model_prediction = detect_lightweight(text, active_classifier)
    model_detection = prediction_to_detection(model_prediction)
    classifier_status = active_classifier.status()

    combined = _dedupe(
        sorted(
            [
                *pii_detections,
                *rule_detections,
                *([model_detection] if model_detection else []),
            ],
            key=lambda item: (
                item.start,
                item.end,
                item.category,
                item.reason_code,
            ),
        )
    )
    primary = max(combined, key=_priority_key) if combined else None

    return HybridDetectionSummary(
        detections=combined,
        reason_codes=sorted({item.reason_code for item in combined}),
        primary_reason_code=primary.reason_code if primary else None,
        risk_score=max(
            (_normalized_score(item) for item in combined),
            default=0.0,
        ),
        classifier_enabled=classifier_status.enabled,
        fallback_used=not classifier_status.enabled,
        model_prediction=model_prediction,
    )


def detect_hybrid_detections(
    text: str,
    classifier: LightweightClassifier | None = None,
) -> list[DetectionResult]:
    return detect_hybrid(text, classifier).detections
