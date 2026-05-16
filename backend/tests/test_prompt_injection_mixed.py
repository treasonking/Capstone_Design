from __future__ import annotations

import json
from pathlib import Path

from backend.app.detection.injection_detector import detect_injection
from backend.app.engine.policy_engine import evaluate_policy


PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = PROJECT_ROOT / "policies" / "policy.yaml"
DATASET_PATH = PROJECT_ROOT / "evaluation" / "datasets" / "prompt_injection_mixed_cases.json"


def _cases() -> list[dict[str, str]]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def test_mixed_prompt_injection_cases_follow_expected_policy() -> None:
    for case in _cases():
        detections = detect_injection(case["text"])
        decision = evaluate_policy(case["text"], detections, POLICY_PATH)

        assert decision.final_action.value == case["expected_action"], case["id"]
        if case["expected_reason"] == "SAFE_INPUT":
            assert decision.reasons == ["SAFE_INPUT"], case["id"]
        else:
            assert case["expected_reason"] in decision.reasons, case["id"]


def test_mixed_safe_security_explanations_are_not_blocked() -> None:
    for case in _cases():
        if case["expected_label"] != "safe":
            continue
        detections = detect_injection(case["text"])
        decision = evaluate_policy(case["text"], detections, POLICY_PATH)

        assert decision.final_action.value != "BLOCK", case["id"]
