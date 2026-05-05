from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any

from .models import DetectionResult, DetectorType
from .reason_codes import ReasonCode

try:
    import joblib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    joblib = None


_MODEL_DIR = Path(__file__).resolve().parents[3] / "models" / "lightweight"
_PII_TERMS = (
    "주민등록번호",
    "주소",
    "연락처",
    "전화",
    "휴대폰",
    "계좌",
    "이메일",
    "rrn",
    "phone",
    "address",
    "account",
    "email",
)
_INJECTION_TERMS = (
    "ignore previous",
    "system prompt",
    "hidden prompt",
    "hidden instruction",
    "internal rule",
    "bypass",
    "developer mode",
    "admin mode",
    "이전 지시",
    "시스템 프롬프트",
    "숨겨진 지시",
    "내부 규칙",
    "우회",
    "개발자 모드",
)
_SAFE_LABELS = {"safe", "benign", "normal", "allow", "none"}


@dataclass(slots=True)
class LightweightModelStatus:
    enabled: bool
    reason: str
    vectorizer_path: Path
    classifier_path: Path


class LightweightClassifier:
    """Optional TF-IDF + Logistic Regression adapter.

    If the serialized vectorizer/classifier pair is missing, the detector stays
    disabled and callers should continue using deterministic regex/rule results.
    """

    def __init__(
        self,
        *,
        vectorizer_path: str | Path | None = None,
        classifier_path: str | Path | None = None,
        threshold: float = 0.6,
    ) -> None:
        self.vectorizer_path = Path(vectorizer_path) if vectorizer_path else _MODEL_DIR / "vectorizer.joblib"
        self.classifier_path = Path(classifier_path) if classifier_path else _MODEL_DIR / "classifier.joblib"
        self.threshold = threshold
        self._load_attempted = False
        self._vectorizer: Any | None = None
        self._classifier: Any | None = None
        self._disabled_reason = "Model load not attempted."

    def status(self) -> LightweightModelStatus:
        self._ensure_loaded()
        return LightweightModelStatus(
            enabled=self.enabled,
            reason=self._disabled_reason,
            vectorizer_path=self.vectorizer_path,
            classifier_path=self.classifier_path,
        )

    @property
    def enabled(self) -> bool:
        return self._vectorizer is not None and self._classifier is not None

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

    def predict(self, text: str) -> DetectionResult | None:
        if not text.strip():
            return None

        self._ensure_loaded()
        if not self.enabled:
            return None

        try:
            features = self._vectorizer.transform([text])
            predicted_label = str(self._classifier.predict(features)[0]).strip().lower()
            confidence = self._confidence(features, predicted_label)
        except Exception:  # pragma: no cover - depends on external artifact implementation
            return None

        if predicted_label in _SAFE_LABELS or confidence < self.threshold:
            return None

        mapped = _map_label(predicted_label)
        if mapped is None:
            return None

        detector_type, category, reason_code = mapped
        evidence_terms = _extract_evidence(text, detector_type)
        return DetectionResult(
            detector_type=detector_type,
            category=category,
            reason_code=reason_code,
            start=0,
            end=0,
            matched_text=", ".join(evidence_terms) if evidence_terms else predicted_label,
            score=round(confidence, 3),
        )

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


def _map_label(label: str) -> tuple[DetectorType, str, str] | None:
    normalized = label.lower()
    if "pii" in normalized or "privacy" in normalized:
        return (DetectorType.PII, "MODEL_PII", ReasonCode.PII_MODEL_RISK_DETECTED.value)
    if "inj" in normalized or "prompt" in normalized or "jailbreak" in normalized:
        return (DetectorType.INJECTION, "MODEL_INJECTION", ReasonCode.INJ_MODEL_RISK_DETECTED.value)
    return None


def _extract_evidence(text: str, detector_type: DetectorType) -> list[str]:
    lowered = text.lower()
    candidate_terms = _PII_TERMS if detector_type == DetectorType.PII else _INJECTION_TERMS
    return [term for term in candidate_terms if term.lower() in lowered][:5]


_DEFAULT_CLASSIFIER = LightweightClassifier()


def get_lightweight_classifier() -> LightweightClassifier:
    return _DEFAULT_CLASSIFIER


def detect_lightweight(text: str, classifier: LightweightClassifier | None = None) -> list[DetectionResult]:
    detector = classifier or get_lightweight_classifier()
    result = detector.predict(text)
    return [result] if result is not None else []
