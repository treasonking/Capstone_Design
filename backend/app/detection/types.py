from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PolicyAction(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    MASK = "MASK"
    BLOCK = "BLOCK"


class DetectorType(str, Enum):
    PII = "PII"
    INJECTION = "INJECTION"
    MODEL = "MODEL"


class DetectionSource(str, Enum):
    REGEX = "regex"
    RULE = "rule"
    MODEL = "model"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(slots=True)
class DetectionResult:
    detector: str
    category: str
    label: str
    confidence: float
    start: int | None = None
    end: int | None = None
    matched_text: str | None = None
    masked_text: str | None = None
    reason_code: str = "UNKNOWN"
    severity: str = SeverityLevel.LOW.value
    source: str = DetectionSource.REGEX.value
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def detector_type(self) -> DetectorType:
        detector_name = self.detector.upper()
        if detector_name.startswith("PII"):
            return DetectorType.PII
        if detector_name.startswith("INJECTION"):
            return DetectorType.INJECTION
        return DetectorType.MODEL

    @property
    def score(self) -> float:
        raw_score = self.metadata.get("raw_score")
        if isinstance(raw_score, (int, float)):
            return float(raw_score)
        return self.confidence

    def with_masked_text(self, masked_text: str | None) -> "DetectionResult":
        return DetectionResult(
            detector=self.detector,
            category=self.category,
            label=self.label,
            confidence=self.confidence,
            start=self.start,
            end=self.end,
            matched_text=self.matched_text,
            masked_text=masked_text,
            reason_code=self.reason_code,
            severity=self.severity,
            source=self.source,
            metadata=dict(self.metadata),
        )


@dataclass(slots=True)
class PolicyRule:
    action: PolicyAction
    priority: int
    threshold: float = 0.0
    description: str = ""


@dataclass(slots=True)
class PolicyDecision:
    final_action: PolicyAction
    reasons: list[str] = field(default_factory=list)
    masked_text: str | None = None
    audit_summary: dict[str, Any] = field(default_factory=dict)
