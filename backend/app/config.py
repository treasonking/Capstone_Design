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


@dataclass(frozen=True, slots=True)
class OllamaSettings:
    enabled: bool = False
    base_url: str = "http://127.0.0.1:11434"
    model: str = "qwen2.5:1.5b"
    timeout_seconds: float = 15.0
    max_input_length: int = 4000
    threshold_margin: float = 0.10


def _bounded_float(name: str, default: float, minimum: float, maximum: float) -> float:
    value = _env_float(name, default)
    return value if minimum <= value <= maximum else default


def get_ollama_settings() -> OllamaSettings:
    defaults = OllamaSettings()
    return OllamaSettings(
        enabled=_env_bool("OLLAMA_ENABLED", defaults.enabled),
        base_url=os.getenv("OLLAMA_BASE_URL", defaults.base_url).strip(),
        model=os.getenv("OLLAMA_MODEL", defaults.model).strip(),
        timeout_seconds=_bounded_float("OLLAMA_TIMEOUT_SECONDS", defaults.timeout_seconds, 0.01, 300),
        max_input_length=int(_bounded_float("OLLAMA_MAX_INPUT_LENGTH", defaults.max_input_length, 1, 4000)),
        threshold_margin=_bounded_float("OLLAMA_THRESHOLD_MARGIN", defaults.threshold_margin, 0, 1),
    )
