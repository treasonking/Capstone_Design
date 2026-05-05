from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
from typing import Any

from backend.app.detection.injection_detector import detect_injection
from backend.app.detection.models import DetectionResult
from backend.app.detection.pii_detector import detect_pii
from backend.app.engine.policy_engine import evaluate_policy
from backend.app.models.lightweight_classifier import detect_model_risk, load_default_lightweight_classifier
from training.prepare_dataset import DEFAULT_OUTPUT_PATH as DEFAULT_DATASET_PATH
from training.prepare_dataset import build_dataset, write_jsonl
from training.split_dataset import DEFAULT_OUTPUT_DIR, assign_splits, load_jsonl, rewrite_dataset, write_splits

try:
    from training.train_lightweight_classifier import train_classifier
except BaseException:  # pragma: no cover
    train_classifier = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
SUMMARY_JSON_PATH = REPORTS_DIR / "evaluation_summary.json"
REPORT_MD_PATH = REPORTS_DIR / "evaluation_report.md"
FALSE_POSITIVES_PATH = REPORTS_DIR / "false_positives.csv"
FALSE_NEGATIVES_PATH = REPORTS_DIR / "false_negatives.csv"
CONFUSION_MATRIX_PATH = REPORTS_DIR / "confusion_matrix.csv"
POLICY_PATH = PROJECT_ROOT / "policies" / "default_policy.yaml"
LABELS = ["safe", "pii_risk", "injection_risk", "mixed_risk", "edge_case"]


def _ensure_dataset() -> Path:
    if not DEFAULT_DATASET_PATH.exists():
        DEFAULT_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(build_dataset(), DEFAULT_DATASET_PATH)
    split_paths = {split: DEFAULT_OUTPUT_DIR / f"{split}.jsonl" for split in ("train", "valid", "test")}
    if not all(path.exists() for path in split_paths.values()):
        records = load_jsonl(DEFAULT_DATASET_PATH)
        assigned = assign_splits(records)
        rewrite_dataset(assigned, DEFAULT_DATASET_PATH)
        write_splits(assigned, DEFAULT_OUTPUT_DIR)
    return DEFAULT_OUTPUT_DIR / "test.jsonl"


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _label_metric(tp: int, fp: int, fn: int) -> dict[str, float | int]:
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def _macro_metrics(confusion: dict[tuple[str, str], int]) -> dict[str, Any]:
    label_metrics: dict[str, dict[str, float | int]] = {}
    for label in LABELS:
        tp = confusion.get((label, label), 0)
        fp = sum(confusion.get((other, label), 0) for other in LABELS if other != label)
        fn = sum(confusion.get((label, other), 0) for other in LABELS if other != label)
        label_metrics[label] = _label_metric(tp, fp, fn)

    macro_precision = sum(metric["precision"] for metric in label_metrics.values()) / len(LABELS)
    macro_recall = sum(metric["recall"] for metric in label_metrics.values()) / len(LABELS)
    macro_f1 = sum(metric["f1"] for metric in label_metrics.values()) / len(LABELS)
    return {
        "precision": macro_precision,
        "recall": macro_recall,
        "f1": macro_f1,
        "label_metrics": label_metrics,
    }


def _load_model_if_needed(mode: str) -> None:
    if mode not in {"model", "hybrid"}:
        return
    runtime = load_default_lightweight_classifier(force_reload=True)
    if runtime.enabled or train_classifier is None:
        return
    try:
        train_classifier(DEFAULT_DATASET_PATH, DEFAULT_OUTPUT_DIR)
    except BaseException:
        return
    load_default_lightweight_classifier(force_reload=True)


def _action_from_label(label: str) -> str:
    return {
        "safe": "ALLOW",
        "pii_risk": "MASK",
        "injection_risk": "BLOCK",
        "mixed_risk": "BLOCK",
        "edge_case": "WARN",
    }.get(label, "ALLOW")


def _hybrid_label(detections: list[DetectionResult], fallback_label: str | None = None) -> str:
    has_pii = any(item.label in {"phone", "email", "resident_number", "address", "account", "card", "ip", "name"} for item in detections if item.detector == "PII_REGEX")
    has_injection = any(item.detector == "INJECTION_RULE" for item in detections)
    model_labels = [item.label for item in detections if item.detector == "LIGHTWEIGHT_MODEL"]

    if has_pii and has_injection:
        return "mixed_risk"
    if has_injection:
        return "injection_risk"
    if has_pii:
        return "pii_risk"
    if "edge_case" in model_labels:
        return "edge_case"
    if "mixed_risk" in model_labels:
        return "mixed_risk"
    if "pii_risk" in model_labels:
        return "pii_risk"
    if "injection_risk" in model_labels:
        return "injection_risk"
    return fallback_label or "safe"


def _predict(text: str, mode: str) -> tuple[str, str, list[DetectionResult]]:
    if mode == "regex":
        detections = detect_pii(text)
        label = "pii_risk" if detections else "safe"
        return label, _action_from_label(label), detections

    if mode == "rule":
        detections = detect_injection(text)
        label = "injection_risk" if detections else "safe"
        return label, _action_from_label(label), detections

    if mode == "model":
        detections = detect_model_risk(text)
        label = detections[0].label if detections else "safe"
        return label, _action_from_label(label), detections

    detections = [*detect_pii(text), *detect_injection(text), *detect_model_risk(text)]
    policy_decision = evaluate_policy(text, detections, POLICY_PATH)
    label = _hybrid_label(detections)
    return label, policy_decision.final_action.value, detections


def _pii_type_detected(expected_type: str, detections: list[DetectionResult]) -> bool:
    mapping = {
        "name": {"name"},
        "phone": {"phone"},
        "email": {"email"},
        "resident_number": {"resident_number"},
        "address": {"address"},
        "account": {"account"},
        "card": {"card"},
        "ip": {"ip"},
    }
    expected_labels = mapping.get(expected_type, {expected_type})
    return any(detection.label in expected_labels for detection in detections)


def _injection_type_detected(expected_type: str, detections: list[DetectionResult]) -> bool:
    category_map = {
        "direct_override": {"DIRECT_OVERRIDE"},
        "system_prompt_leak": {"SYSTEM_PROMPT"},
        "role_play_bypass": {"ROLE_OVERRIDE", "DEBUG_MODE"},
        "data_exfiltration": {"DATA_EXFILTRATION"},
        "multi_step": {"MULTI_STEP"},
        "obfuscated": {"OBFUSCATED"},
        "indirect": {"RULE_DISCLOSURE"},
        "none": set(),
    }
    expected_categories = category_map.get(expected_type, {expected_type.upper()})
    return any(detection.category in expected_categories for detection in detections)


def _csv_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        rows.append(
            {
                "id": record["id"],
                "expected_label": record["expected_label"],
                "predicted_label": record["predicted_label"],
                "expected_action": record["expected_action"],
                "predicted_action": record["predicted_action"],
                "reason_codes": ",".join(record["reason_codes"]),
                "text_excerpt": record["text"][:160],
                "mode": record["mode"],
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        rows = [{"id": "-", "expected_label": "-", "predicted_label": "-", "expected_action": "-", "predicted_action": "-", "reason_codes": "-", "text_excerpt": "-", "mode": "-"}]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_confusion_matrix(path: Path, confusion: dict[tuple[str, str], int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["expected\\predicted", *LABELS])
        for expected in LABELS:
            writer.writerow([expected, *[confusion.get((expected, predicted), 0) for predicted in LABELS]])


def _load_summary() -> dict[str, Any]:
    if not SUMMARY_JSON_PATH.exists():
        return {"modes": {}}
    return json.loads(SUMMARY_JSON_PATH.read_text(encoding="utf-8"))


def _save_summary(summary: dict[str, Any]) -> None:
    SUMMARY_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_JSON_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def _render_report(summary: dict[str, Any], current_mode: str, metrics: dict[str, Any]) -> None:
    mode_notes = {
        "regex": "Structured PII detection only.",
        "rule": "Prompt injection rule detection only.",
        "model": "Lightweight context classification only.",
        "hybrid": "Final proposed hybrid proxy.",
    }
    lines = [
        "# Hybrid Detection Evaluation Report",
        "",
        f"- Current mode: `{current_mode}`",
        f"- Dataset: `{metrics['dataset_path']}`",
        f"- Samples evaluated: **{metrics['sample_count']}**",
        "",
        "## Mode Comparison",
        "",
        "| Mode | Precision | Recall | F1 | Notes |",
        "|---|---:|---:|---:|---|",
    ]
    for mode in ("regex", "rule", "model", "hybrid"):
        mode_metric = summary.get("modes", {}).get(mode)
        if not mode_metric:
            lines.append(f"| {mode.title()} | - | - | - | {mode_notes[mode]} |")
            continue
        lines.append(
            f"| {mode.title()} | {mode_metric['precision']:.3f} | {mode_metric['recall']:.3f} | {mode_metric['f1']:.3f} | {mode_notes[mode]} |"
        )
    lines.extend(
        [
            "",
            "## Label Metrics",
            "",
            "| Label | Precision | Recall | F1 | TP | FP | FN |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for label, metric in metrics["label_metrics"].items():
        lines.append(
            f"| {label} | {metric['precision']:.3f} | {metric['recall']:.3f} | {metric['f1']:.3f} | {metric['tp']} | {metric['fp']} | {metric['fn']} |"
        )

    lines.extend(["", "## PII Type Detection Rate", "", "| PII Type | Detection Rate |", "|---|---:|"])
    for pii_type, value in sorted(metrics["pii_type_detection"].items()):
        lines.append(f"| {pii_type} | {value:.3f} |")

    lines.extend(["", "## Injection Type Detection Rate", "", "| Injection Type | Detection Rate |", "|---|---:|"])
    for injection_type, value in sorted(metrics["injection_type_detection"].items()):
        lines.append(f"| {injection_type} | {value:.3f} |")

    lines.extend(
        [
            "",
            "## Error Artifacts",
            "",
            "- False positives: `reports/false_positives.csv`",
            "- False negatives: `reports/false_negatives.csv`",
            "- Confusion matrix: `reports/confusion_matrix.csv`",
        ]
    )
    REPORT_MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def evaluate_mode(mode: str, dataset_path: Path) -> dict[str, Any]:
    _load_model_if_needed(mode)
    records = load_jsonl(dataset_path)
    confusion: dict[tuple[str, str], int] = Counter()
    false_positives: list[dict[str, Any]] = []
    false_negatives: list[dict[str, Any]] = []
    pii_hits: Counter[str] = Counter()
    pii_totals: Counter[str] = Counter()
    injection_hits: Counter[str] = Counter()
    injection_totals: Counter[str] = Counter()

    for record in records:
        expected_label = str(record["label"])
        predicted_label, predicted_action, detections = _predict(str(record["text"]), mode)
        confusion[(expected_label, predicted_label)] += 1

        entry = {
            "id": record["id"],
            "expected_label": expected_label,
            "predicted_label": predicted_label,
            "expected_action": record["expected_action"],
            "predicted_action": predicted_action,
            "reason_codes": [item.reason_code for item in detections],
            "text": record["text"],
            "mode": mode,
        }
        if expected_label == "safe" and predicted_label != "safe":
            false_positives.append(entry)
        if expected_label != "safe" and predicted_label == "safe":
            false_negatives.append(entry)
        if expected_label != "safe" and predicted_label != expected_label and predicted_label != "safe":
            false_negatives.append(entry)

        for pii_type in record.get("pii_types", []):
            pii_type = str(pii_type)
            pii_totals[pii_type] += 1
            if _pii_type_detected(pii_type, detections):
                pii_hits[pii_type] += 1

        for injection_type in record.get("injection_types", []):
            injection_type = str(injection_type)
            if injection_type == "none":
                continue
            injection_totals[injection_type] += 1
            if _injection_type_detected(injection_type, detections):
                injection_hits[injection_type] += 1

    aggregate = _macro_metrics(confusion)
    metrics = {
        "mode": mode,
        "dataset_path": str(dataset_path),
        "sample_count": len(records),
        "precision": aggregate["precision"],
        "recall": aggregate["recall"],
        "f1": aggregate["f1"],
        "label_metrics": aggregate["label_metrics"],
        "pii_type_detection": {
            key: _safe_div(pii_hits[key], pii_totals[key]) for key in sorted(pii_totals)
        },
        "injection_type_detection": {
            key: _safe_div(injection_hits[key], injection_totals[key]) for key in sorted(injection_totals)
        },
        "false_positives": _csv_rows(false_positives),
        "false_negatives": _csv_rows(false_negatives),
    }
    _write_csv(FALSE_POSITIVES_PATH, metrics["false_positives"])
    _write_csv(FALSE_NEGATIVES_PATH, metrics["false_negatives"])
    _write_confusion_matrix(CONFUSION_MATRIX_PATH, confusion)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate regex, rule, model, or hybrid detection modes.")
    parser.add_argument("--mode", required=True, choices=["regex", "rule", "model", "hybrid"], help="Evaluation mode.")
    parser.add_argument("--dataset", default=str(_ensure_dataset()), help="Path to processed test JSONL dataset.")
    args = parser.parse_args()

    metrics = evaluate_mode(args.mode, Path(args.dataset))
    summary = _load_summary()
    summary.setdefault("modes", {})[args.mode] = {
        key: value
        for key, value in metrics.items()
        if key not in {"false_positives", "false_negatives"}
    }
    _save_summary(summary)
    _render_report(summary, args.mode, metrics)

    print(json.dumps({"mode": args.mode, "precision": metrics["precision"], "recall": metrics["recall"], "f1": metrics["f1"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
