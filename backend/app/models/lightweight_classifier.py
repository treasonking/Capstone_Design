from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from backend.app.detection.models import DetectionResult
from backend.app.detection.reason_codes import ReasonCode
from backend.app.models.model_config import (
    CLASSIFIER_PATH,
    DEFAULT_MODEL_VERSION,
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
    METADATA_PATH,
    SUPPORTED_LABELS,
    VECTORIZER_PATH,
)

try:
    import joblib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    joblib = None


@dataclass(slots=True)
class LightweightClassifier:
    enabled: bool
    vectorizer: Any = None
    classifier: Any = None
    model_version: str = DEFAULT_MODEL_VERSION
    disabled_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def predict(self, text: str) -> tuple[str, float, dict[str, float]] | None:
        if not self.enabled or not text.strip():
            return None
        features = self.vectorizer.transform([text])
        label = str(self.classifier.predict(features)[0])
        probabilities: dict[str, float] = {}
        confidence = 0.0

        if hasattr(self.classifier, "predict_proba"):
            raw_probabilities = self.classifier.predict_proba(features)[0]
            labels = [str(item) for item in self.classifier.classes_]
            probabilities = {
                class_name: float(raw_probabilities[index])
                for index, class_name in enumerate(labels)
            }
            confidence = probabilities.get(label, max(probabilities.values(), default=0.0))

        return label, confidence, probabilities


_DEFAULT_CLASSIFIER: LightweightClassifier | None = None


def _metadata(model_dir: Path) -> dict[str, Any]:
    metadata_path = model_dir / METADATA_PATH.name
    if not metadata_path.exists():
        return {"model_version": DEFAULT_MODEL_VERSION}
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"model_version": DEFAULT_MODEL_VERSION}


def load_lightweight_classifier(
    *,
    vectorizer_path: str | Path = VECTORIZER_PATH,
    classifier_path: str | Path = CLASSIFIER_PATH,
) -> LightweightClassifier:
    vectorizer_file = Path(vectorizer_path)
    classifier_file = Path(classifier_path)
    model_dir = vectorizer_file.parent
    metadata = _metadata(model_dir)
    model_version = str(metadata.get("model_version", DEFAULT_MODEL_VERSION))

    if joblib is None:
        return LightweightClassifier(
            enabled=False,
            model_version=model_version,
            disabled_reason="joblib_not_installed",
            metadata=metadata,
        )
    if not vectorizer_file.exists() or not classifier_file.exists():
        return LightweightClassifier(
            enabled=False,
            model_version=model_version,
            disabled_reason="model_files_missing",
            metadata=metadata,
        )

    try:
        vectorizer = joblib.load(vectorizer_file)
        classifier = joblib.load(classifier_file)
    except Exception as exc:  # pragma: no cover
        return LightweightClassifier(
            enabled=False,
            model_version=model_version,
            disabled_reason=f"model_load_failed:{type(exc).__name__}",
            metadata=metadata,
        )

    return LightweightClassifier(
        enabled=True,
        vectorizer=vectorizer,
        classifier=classifier,
        model_version=model_version,
        metadata=metadata,
    )


def load_default_lightweight_classifier(force_reload: bool = False) -> LightweightClassifier:
    global _DEFAULT_CLASSIFIER
    if _DEFAULT_CLASSIFIER is None or force_reload:
        _DEFAULT_CLASSIFIER = load_lightweight_classifier()
    return _DEFAULT_CLASSIFIER


def _result(reason_code: str, label: str, confidence: float, model_version: str, probabilities: dict[str, float]) -> DetectionResult:
    severity = "HIGH" if confidence >= HIGH_CONFIDENCE_THRESHOLD else "MEDIUM"
    return DetectionResult(
        detector="LIGHTWEIGHT_MODEL",
        category="MODEL_RISK",
        label=label,
        confidence=confidence,
        start=None,
        end=None,
        matched_text=None,
        masked_text=None,
        reason_code=reason_code,
        severity=severity,
        source="model",
        metadata={
            "model_version": model_version,
            "probabilities": probabilities,
        },
    )


def detect_model_risk(text: str, classifier: LightweightClassifier | None = None) -> list[DetectionResult]:
    runtime = classifier or load_default_lightweight_classifier()
    prediction = runtime.predict(text)
    if prediction is None:
        return []

    label, confidence, probabilities = prediction
    reason_code = {
        "pii_risk": ReasonCode.MODEL_PII_RISK.value,
        "injection_risk": ReasonCode.MODEL_INJECTION_RISK.value,
        "mixed_risk": ReasonCode.MODEL_MIXED_RISK.value,
        "edge_case": ReasonCode.MODEL_EDGE_CASE.value,
    }.get(label)
    if reason_code is None:
        return []

    if confidence < MEDIUM_CONFIDENCE_THRESHOLD:
        return []

    if label not in SUPPORTED_LABELS:
        return []
    return [_result(reason_code, label, confidence, runtime.model_version, probabilities)]
