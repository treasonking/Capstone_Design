from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised when dependency is absent.
    yaml = None

from backend.app.detection.models import DetectionResult, PolicyAction, PolicyDecision, PolicyRule
from backend.app.detection.reason_codes import ReasonCode
from backend.app.engine.masking import apply_masking


_ACTION_WEIGHT = {
    PolicyAction.BLOCK: 4,
    PolicyAction.MASK: 3,
    PolicyAction.WARN: 2,
    PolicyAction.ALLOW: 1,
}


def load_policy(policy_path: str | Path) -> dict[str, Any]:
    text = Path(policy_path).read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    return _load_policy_fallback(text)


def _parse_scalar(raw_value: str) -> Any:
    value = raw_value.strip().strip('"').strip("'")
    if value.replace(".", "", 1).isdigit():
        return float(value) if "." in value else int(value)
    return value


def _load_policy_fallback(text: str) -> dict[str, Any]:
    """
    Minimal YAML parser for this project policy format.
    Supports:
      - top-level scalar fields
      - rules:<reason_code>:<scalar fields>
    """
    data: dict[str, Any] = {"rules": {}}
    current_rule: dict[str, Any] | None = None
    current_rule_name: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if line.startswith("default_action:"):
            data["default_action"] = _parse_scalar(line.split(":", 1)[1])
            continue
        if line.strip() == "rules:":
            continue
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            current_rule_name = line.strip()[:-1]
            current_rule = {}
            data["rules"][current_rule_name] = current_rule
            continue
        if line.startswith("    ") and ":" in line and current_rule is not None:
            key, value = line.strip().split(":", 1)
            current_rule[key] = _parse_scalar(value)
    return data


def _parse_rule(raw_rule: dict[str, Any]) -> PolicyRule:
    action = PolicyAction(str(raw_rule.get("action", PolicyAction.ALLOW.value)).upper())
    return PolicyRule(
        action=action,
        priority=int(raw_rule.get("priority", 0)),
        threshold=float(raw_rule.get("threshold", 0.0)),
        description=str(raw_rule.get("description", "")),
    )


def _eligible_detections(
    detections: list[DetectionResult],
    rule_map: dict[str, PolicyRule],
) -> list[tuple[DetectionResult, PolicyRule]]:
    eligible: list[tuple[DetectionResult, PolicyRule]] = []
    for detection in detections:
        rule = rule_map.get(
            detection.reason_code,
            PolicyRule(action=PolicyAction.ALLOW, priority=0, threshold=0.0),
        )
        if detection.score >= rule.threshold:
            eligible.append((detection, rule))
    return eligible


def evaluate_policy(
    text: str,
    detections: list[DetectionResult],
    policy_path: str | Path,
) -> PolicyDecision:
    policy_data = load_policy(policy_path)
    default_action = PolicyAction(str(policy_data.get("default_action", "ALLOW")).upper())
    raw_rules = policy_data.get("rules", {})
    rule_map = {reason: _parse_rule(rule) for reason, rule in raw_rules.items()}

    eligible = _eligible_detections(detections, rule_map)
    if not eligible:
        return PolicyDecision(
            final_action=default_action,
            reasons=[ReasonCode.SAFE_INPUT.value],
            masked_text=None,
            audit_summary={
                "total_detections": 0,
                "detector_counts": {},
                "applied_rule_count": 0,
            },
        )

    winner_detection, winner_rule = max(
        eligible,
        key=lambda item: (item[1].priority, _ACTION_WEIGHT[item[1].action]),
    )
    reasons = sorted({item[0].reason_code for item in eligible})

    masked_text = None
    if winner_rule.action == PolicyAction.MASK:
        masked_text = apply_masking(text, [item[0] for item in eligible])

    detector_counts = Counter(item[0].detector_type.value for item in eligible)
    audit_summary = {
        "total_detections": len(eligible),
        "detector_counts": dict(detector_counts),
        "applied_rule_count": len(reasons),
        "winning_reason": winner_detection.reason_code,
    }

    return PolicyDecision(
        final_action=winner_rule.action,
        reasons=reasons,
        masked_text=masked_text,
        audit_summary=audit_summary,
    )
