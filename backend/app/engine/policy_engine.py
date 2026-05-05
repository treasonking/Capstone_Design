from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
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
        if line.startswith("policy_version:"):
            data["policy_version"] = _parse_scalar(line.split(":", 1)[1])
            continue
        if line.startswith("model_version:"):
            data["model_version"] = _parse_scalar(line.split(":", 1)[1])
            continue
        if line.strip() == "rules:":
            continue
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            current_rule_name = line.strip()[:-1]
            current_rule = {}
            data["rules"][current_rule_name] = current_rule
            continue
        if line.startswith("    ") and ":" in line and current_rule is not None and current_rule_name is not None:
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


def _raw_rules_from_policy(policy_data: dict[str, Any]) -> dict[str, Any]:
    raw_rules = policy_data.get("rules")
    if isinstance(raw_rules, dict):
        return raw_rules
    nested_rules = policy_data.get("policy", {}).get("rules", {})
    return nested_rules if isinstance(nested_rules, dict) else {}


def _eligible_detections(
    detections: list[DetectionResult],
    rule_map: dict[str, PolicyRule],
) -> list[tuple[DetectionResult, PolicyRule]]:
    eligible: list[tuple[DetectionResult, PolicyRule]] = []
    for detection in detections:
        rule = rule_map.get(
            detection.reason_code,
            PolicyRule(action=PolicyAction.ALLOW, priority=0, threshold=1.1),
        )
        if detection.score >= rule.threshold:
            eligible.append((detection, rule))
    return eligible


def _injection_audit(eligible: list[tuple[DetectionResult, PolicyRule]]) -> dict[str, Any] | None:
    injection_items = [item for item in eligible if item[0].detector_type.value == "INJECTION"]
    if not injection_items:
        return None

    injection_detections = [detection for detection, _rule in injection_items]
    matched_terms: list[str] = []
    for detection in injection_detections:
        if detection.matched_text:
            matched_terms.extend(term.strip() for term in detection.matched_text.split(",") if term.strip())

    winning_detection, winning_rule = max(
        injection_items,
        key=lambda item: (item[1].priority, _ACTION_WEIGHT[item[1].action], item[0].score),
    )
    return {
        "detector": "PROMPT_INJECTION",
        "score": max(detection.score for detection in injection_detections),
        "action": winning_rule.action.value,
        "reason_code": winning_detection.reason_code,
        "matched_categories": sorted({detection.category for detection in injection_detections}),
        "matched_terms": sorted(set(matched_terms)),
    }


def _model_audit(eligible: list[tuple[DetectionResult, PolicyRule]]) -> dict[str, Any] | None:
    model_items = [item for item in eligible if item[0].detector_type.value == "MODEL"]
    if not model_items:
        return None
    top_detection, top_rule = max(
        model_items,
        key=lambda item: (item[1].priority, _ACTION_WEIGHT[item[1].action], item[0].score),
    )
    return {
        "detector": "LIGHTWEIGHT_MODEL",
        "score": round(top_detection.score, 4),
        "label": top_detection.label,
        "reason_code": top_detection.reason_code,
        "action": top_rule.action.value,
    }


def _maskable_detections(eligible: list[tuple[DetectionResult, PolicyRule]]) -> list[DetectionResult]:
    maskable: list[DetectionResult] = []
    for detection, rule in eligible:
        if detection.detector_type.value != "PII":
            continue
        if rule.action not in {PolicyAction.MASK, PolicyAction.BLOCK}:
            continue
        if detection.start is None or detection.end is None or not detection.matched_text:
            continue
        maskable.append(detection)
    return maskable


def evaluate_policy(
    text: str,
    detections: list[DetectionResult],
    policy_path: str | Path,
) -> PolicyDecision:
    policy_data = load_policy(policy_path)
    default_action = PolicyAction(str(policy_data.get("default_action", "ALLOW")).upper())
    policy_version = str(policy_data.get("policy_version", "default-policy-v2"))
    model_version = str(policy_data.get("model_version", "lightweight-tfidf-logreg"))
    raw_rules = _raw_rules_from_policy(policy_data)
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
                "source_counts": {},
                "category_counts": {},
                "applied_rule_count": 0,
                "policy_version": policy_version,
                "model_version": model_version,
            },
        )

    winner_detection, winner_rule = max(
        eligible,
        key=lambda item: (item[1].priority, _ACTION_WEIGHT[item[1].action], item[0].score),
    )
    reasons = sorted({item[0].reason_code for item in eligible})

    masked_text = None
    if winner_rule.action == PolicyAction.MASK:
        masked_text = apply_masking(text, _maskable_detections(eligible))

    detector_counts = Counter(item[0].detector_type.value for item in eligible)
    source_counts = Counter(item[0].source for item in eligible)
    category_counts = Counter(item[0].category for item in eligible)
    audit_summary = {
        "total_detections": len(eligible),
        "detector_counts": dict(detector_counts),
        "source_counts": dict(source_counts),
        "category_counts": dict(category_counts),
        "applied_rule_count": len(reasons),
        "winning_reason": winner_detection.reason_code,
        "winning_action": winner_rule.action.value,
        "matched_labels": sorted({item[0].label for item in eligible}),
        "policy_version": policy_version,
        "model_version": model_version,
    }

    injection_audit = _injection_audit(eligible)
    if injection_audit is not None:
        audit_summary["prompt_injection"] = injection_audit

    model_audit = _model_audit(eligible)
    if model_audit is not None:
        audit_summary["model_signal"] = model_audit

    return PolicyDecision(
        final_action=winner_rule.action,
        reasons=reasons,
        masked_text=masked_text,
        audit_summary=audit_summary,
    )
