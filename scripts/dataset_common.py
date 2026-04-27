from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any


VALID_TASKS = {"pii", "injection"}

VALID_LABELS = {
    "PII_EMAIL_DETECTED",
    "PII_PHONE_DETECTED",
    "PII_RRN_DETECTED",
    "PII_ACCOUNT_DETECTED",
    "INJ_DIRECT_OVERRIDE_ATTEMPT",
    "INJ_IGNORE_PREVIOUS_INSTRUCTIONS",
    "INJ_REVEAL_SYSTEM_PROMPT",
    "INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT",
    "INJ_POLICY_BYPASS_ATTEMPT",
    "INJ_ROLE_OVERRIDE_ATTEMPT",
    "INJ_DEBUG_MODE_ATTEMPT",
    "INJ_RULE_DISCLOSURE_ATTEMPT",
    "INJ_MULTI_STEP_EXTRACTION_ATTEMPT",
    "INJ_OBFUSCATED_INJECTION_ATTEMPT",
}

PII_LABELS = {label for label in VALID_LABELS if label.startswith("PII_")}
INJECTION_LABELS = {label for label in VALID_LABELS if label.startswith("INJ_")}


def load_dataset(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Dataset root must be a JSON list.")
    return data


def labels_for_task(task: str) -> set[str]:
    if task == "pii":
        return PII_LABELS
    if task == "injection":
        return INJECTION_LABELS
    return set()


def counter_to_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: item[0]))
