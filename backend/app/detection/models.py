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


@dataclass(slots=True)
class DetectionResult:
    detector_type: DetectorType
    category: str
    reason_code: str
    start: int
    end: int
    matched_text: str
    score: float = 1.0
    detector_name: str = "regex"


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


@dataclass(slots=True)
class DetectorRunSummary:
    detector: str
    action: str
    reasons: list[str] = field(default_factory=list)
    pii_detected: bool = False
    injection_detected: bool = False
    confidence: float | None = None
    status: str = "completed"

    @property
    def reason_code(self) -> str | None:
        return self.reasons[0] if self.reasons else None

