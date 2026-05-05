from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LIGHTWEIGHT_MODEL_DIR = PROJECT_ROOT / "models" / "lightweight"
VECTORIZER_PATH = LIGHTWEIGHT_MODEL_DIR / "vectorizer.joblib"
CLASSIFIER_PATH = LIGHTWEIGHT_MODEL_DIR / "classifier.joblib"
METADATA_PATH = LIGHTWEIGHT_MODEL_DIR / "metadata.json"
DEFAULT_MODEL_VERSION = "lightweight-tfidf-logreg-v1"
HIGH_CONFIDENCE_THRESHOLD = 0.90
MEDIUM_CONFIDENCE_THRESHOLD = 0.70
SUPPORTED_LABELS = ("safe", "pii_risk", "injection_risk", "mixed_risk", "edge_case")
