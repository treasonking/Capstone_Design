from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import DetectionResult, DetectorType
from .reason_codes import ReasonCode

try:
    import joblib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    joblib = None


_MODEL_DIR = Path(__file__).resolve().parents[3] / "models" / "lightweight"
_SAFE_LABELS = {"safe", "benign", "normal", "allow", "none"}
_SOURCE_MODEL = "lightweight_model"
_SOURCE_FALLBACK = "fallback_disabled"


@dataclass(slots=True)
class LightweightModelStatus:
    enabled: bool
    reason: str
    vectorizer_path: Path
    classifier_path: Path


@dataclass(slots=True)
class LightweightPrediction:
    detected: bool
    confidence: float
    reason_code: str | None
    label: str
    source: str


class LightweightClassifier:
    """Optional TF-IDF + Logistic Regression adapter with safe fallback."""

    def __init__(
        self,
        *,
        vectorizer_path: str | Path | None = None,
        classifier_path: str | Path | None = None,
        threshold: float = 0.6,
    ) -> None:
        self.vectorizer_path = (
            Path(vectorizer_path)
            if vectorizer_path
            else _MODEL_DIR / "vectorizer.joblib"
        )
        self.classifier_path = (
            Path(classifier_path)
            if classifier_path
            else _MODEL_DIR / "classifier.joblib"
        )
        self.threshold = threshold
        self._load_attempted = False
        self._vectorizer: Any | None = None
        self._classifier: Any | None = None
        self._disabled_reason = "Model load not attempted."

    @property
    def enabled(self) -> bool:
        return self._vectorizer is not None and self._classifier is not None

    def status(self) -> LightweightModelStatus:
        self._ensure_loaded()
        return LightweightModelStatus(
            enabled=self.enabled,
            reason=self._disabled_reason,
            vectorizer_path=self.vectorizer_path,
            classifier_path=self.classifier_path,
        )

    def classify(self, text: str) -> LightweightPrediction:
        if not text.strip():
            return LightweightPrediction(
                detected=False,
                confidence=0.0,
                reason_code=None,
                label="empty",
                source=_SOURCE_FALLBACK,
            )

        self._ensure_loaded()
        if not self.enabled:
            return LightweightPrediction(
                detected=False,
                confidence=0.0,
                reason_code=None,
                label="unavailable",
                source=_SOURCE_FALLBACK,
            )

        try:
            features = self._vectorizer.transform([text])
            predicted_label = str(self._classifier.predict(features)[0]).strip().lower()
            confidence = round(self._confidence(features, predicted_label), 3)
        except Exception:  # pragma: no cover - depends on external artifact implementation
            return LightweightPrediction(
                detected=False,
                confidence=0.0,
                reason_code=None,
                label="error",
                source=_SOURCE_FALLBACK,
            )

        mapped = _map_label(predicted_label)
        if predicted_label in _SAFE_LABELS or mapped is None or confidence < self.threshold:
            return LightweightPrediction(
                detected=False,
                confidence=confidence,
                reason_code=None,
                label=predicted_label,
                source=_SOURCE_MODEL,
            )

        return LightweightPrediction(
            detected=True,
            confidence=confidence,
            reason_code=mapped.reason_code,
            label=mapped.label,
            source=_SOURCE_MODEL,
        )

    def _ensure_loaded(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True

        if joblib is None:
            self._disabled_reason = "Optional dependency 'joblib' is not installed."
            return
        if not self.vectorizer_path.exists() or not self.classifier_path.exists():
            self._disabled_reason = "Model artifact files are missing."
            return

        try:
            self._vectorizer = joblib.load(self.vectorizer_path)
            self._classifier = joblib.load(self.classifier_path)
            self._disabled_reason = "Model loaded."
        except Exception as exc:  # pragma: no cover - defensive for arbitrary artifact issues
            self._vectorizer = None
            self._classifier = None
            self._disabled_reason = f"Model artifact load failed: {exc.__class__.__name__}"

    def _confidence(self, features: Any, predicted_label: str) -> float:
        if hasattr(self._classifier, "predict_proba"):
            probabilities = self._classifier.predict_proba(features)[0]
            classes = [str(item).strip().lower() for item in getattr(self._classifier, "classes_", [])]
            if predicted_label in classes:
                return float(probabilities[classes.index(predicted_label)])
            return float(max(probabilities))

        if hasattr(self._classifier, "decision_function"):
            margin = self._classifier.decision_function(features)
            if hasattr(margin, "__len__"):
                value = float(margin[0] if len(margin) == 1 else max(margin[0]))
            else:
                value = float(margin)
            return 1.0 / (1.0 + math.exp(-value))

        return 1.0


@dataclass(frozen=True, slots=True)
class _LabelMapping:
    detector_type: DetectorType
    label: str
    reason_code: str


def _map_label(label: str) -> _LabelMapping | None:
    normalized = label.lower()
    if "pii" in normalized or "privacy" in normalized:
        return _LabelMapping(
            DetectorType.PII,
            "pii_risk",
            ReasonCode.MODEL_PII_RISK.value,
        )
    if "inj" in normalized or "prompt" in normalized or "jailbreak" in normalized:
        return _LabelMapping(
            DetectorType.INJECTION,
            "injection_risk",
            ReasonCode.MODEL_INJECTION_RISK.value,
        )
    return None


def prediction_to_detection(prediction: LightweightPrediction) -> DetectionResult | None:
    if not prediction.detected or not prediction.reason_code:
        return None

    mapping = _map_label(prediction.label)
    if mapping is None:
        if prediction.reason_code == ReasonCode.MODEL_PII_RISK.value:
            mapping = _LabelMapping(DetectorType.PII, "pii_risk", prediction.reason_code)
        elif prediction.reason_code == ReasonCode.MODEL_INJECTION_RISK.value:
            mapping = _LabelMapping(DetectorType.INJECTION, "injection_risk", prediction.reason_code)
        else:
            return None

    category = "MODEL_PII" if mapping.detector_type == DetectorType.PII else "MODEL_INJECTION"
    return DetectionResult(
        detector_type=mapping.detector_type,
        category=category,
        reason_code=mapping.reason_code,
        start=0,
        end=0,
        matched_text=f"{prediction.source}:{prediction.label}",
        score=prediction.confidence,
    )


_DEFAULT_CLASSIFIER = LightweightClassifier()


def get_lightweight_classifier() -> LightweightClassifier:
    return _DEFAULT_CLASSIFIER


def detect_lightweight(text: str, classifier: LightweightClassifier | None = None) -> LightweightPrediction:
    detector = classifier or get_lightweight_classifier()
    return detector.classify(text)
