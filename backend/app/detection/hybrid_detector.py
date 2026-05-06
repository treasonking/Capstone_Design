from __future__ import annotations

from dataclasses import dataclass, field

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
class HybridDetectionResult:
    detections: list[DetectionResult]
    model_enabled: bool
    model_status: str
    fallback_used: bool
    model_label: str | None = None
    model_confidence: float | None = None
    reason_codes: list[str] = field(default_factory=list)
    primary_reason_code: str | None = None
    risk_score: float = 0.0
    model_prediction: LightweightPrediction | None = None

    @property
    def classifier_enabled(self) -> bool:
        return self.model_enabled


HybridDetectionSummary = HybridDetectionResult


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
) -> HybridDetectionResult:
    pii_detections = detect_pii(text)
    rule_detections = detect_injection(text)
    active_classifier = classifier or get_lightweight_classifier()
    model_prediction = detect_lightweight(text, active_classifier)
    classifier_status = active_classifier.status()
    model_detection = prediction_to_detection(model_prediction)

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

    model_label = (
        model_prediction.label
        if model_prediction.source == "lightweight_model"
        else None
    )
    model_confidence = (
        round(model_prediction.confidence, 3)
        if model_prediction.source == "lightweight_model"
        else None
    )

    return HybridDetectionResult(
        detections=combined,
        model_enabled=classifier_status.enabled,
        model_status=classifier_status.status,
        model_label=model_label,
        model_confidence=model_confidence,
        fallback_used=classifier_status.status != "enabled",
        reason_codes=sorted({item.reason_code for item in combined}),
        primary_reason_code=primary.reason_code if primary else None,
        risk_score=max((_normalized_score(item) for item in combined), default=0.0),
        model_prediction=model_prediction,
    )


def detect_hybrid_detections(
    text: str,
    classifier: LightweightClassifier | None = None,
) -> list[DetectionResult]:
    return detect_hybrid(text, classifier).detections
