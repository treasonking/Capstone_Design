from __future__ import annotations

import os
from dataclasses import dataclass


_FALSE_VALUES = {"0", "false", "off", "no"}
_TRUE_VALUES = {"1", "true", "on", "yes"}
_DETECTION_MODES = {"regex_only", "model_only", "hybrid"}
_FAIL_MODES = {"allow", "warn", "block"}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default

    normalized = raw.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_choice(name: str, default: str, allowed: set[str]) -> str:
    raw = os.getenv(name)
    if raw is None:
        return default

    normalized = raw.strip().lower()
    if normalized in allowed:
        return normalized
    return default


@dataclass(slots=True)
class DetectionSettings:
    enable_model_detector: bool = True
    detection_mode: str = "hybrid"
    model_detector_threshold: float = 0.7
    model_detector_fail_mode: str = "warn"

    @property
    def model_detector_requested(self) -> bool:
        return self.enable_model_detector and self.detection_mode in {"hybrid", "model_only"}

    @property
    def regex_detector_requested(self) -> bool:
        return self.detection_mode in {"hybrid", "regex_only"}


def get_detection_settings() -> DetectionSettings:
    return DetectionSettings(
        enable_model_detector=_env_bool("ENABLE_MODEL_DETECTOR", True),
        detection_mode=_env_choice("DETECTION_MODE", "hybrid", _DETECTION_MODES),
        model_detector_threshold=_env_float("MODEL_DETECTOR_THRESHOLD", 0.7),
        model_detector_fail_mode=_env_choice("MODEL_DETECTOR_FAIL_MODE", "warn", _FAIL_MODES),
    )
