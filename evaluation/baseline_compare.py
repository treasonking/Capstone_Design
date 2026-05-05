from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from backend.app.detection.hybrid_detector import detect_hybrid
from backend.app.detection.injection_detector import detect_injection
from backend.app.detection.lightweight_classifier import get_lightweight_classifier
from backend.app.detection.models import DetectionResult, DetectorType
from backend.app.detection.pii_detector import detect_pii


DetectorFunc = Callable[[str, str], list[DetectionResult]]


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _metric(tp: int, fp: int, fn: int, tn: int) -> dict[str, Any]:
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    accuracy = _safe_div(tp + tn, tp + fp + fn + tn)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
    }


def _expected_positive(row: dict[str, Any]) -> bool:
    return bool(row.get("labels", []))


def _task_detector_type(task: str) -> DetectorType:
    return DetectorType.PII if task == "pii" else DetectorType.INJECTION


def _regex_only(text: str, task: str) -> list[DetectionResult]:
    if task != "pii":
        return []
    return detect_pii(text)


def _rule_only(text: str, task: str) -> list[DetectionResult]:
    if task != "injection":
        return []
    return detect_injection(text)


def _model_only(text: str, task: str) -> list[DetectionResult]:
    summary = detect_hybrid(text)
    target_type = _task_detector_type(task)
    return [
        item
        for item in summary.detections
        if item.category.startswith("MODEL_") and item.detector_type == target_type
    ]


def _hybrid(text: str, task: str) -> list[DetectionResult]:
    summary = detect_hybrid(text)
    target_type = _task_detector_type(task)
    return [item for item in summary.detections if item.detector_type == target_type]


def _evaluate(dataset: list[dict[str, Any]], detector: DetectorFunc) -> dict[str, Any]:
    task_rows = {"pii": [], "injection": []}
    for row in dataset:
        task_rows[str(row.get("task", ""))].append(row)

    result: dict[str, Any] = {}
    for task in ("pii", "injection"):
        tp = fp = fn = tn = 0
        for row in task_rows[task]:
            predicted_positive = bool(detector(str(row.get("text", "")), task))
            expected_positive = _expected_positive(row)
            if predicted_positive and expected_positive:
                tp += 1
            elif predicted_positive and not expected_positive:
                fp += 1
            elif not predicted_positive and expected_positive:
                fn += 1
            else:
                tn += 1
        result[task] = _metric(tp, fp, fn, tn)
    return result


def _render_report(
    comparisons: dict[str, dict[str, Any]],
    statuses: dict[str, str],
    *,
    dataset_path: str,
    output_path: Path,
) -> Path:
    classifier_status = get_lightweight_classifier().status()
    lines = [
        "# Baseline Comparison Report",
        "",
        f"- Dataset: `{dataset_path}`",
        f"- Lightweight model enabled: `{classifier_status.enabled}`",
        f"- Lightweight model status: {classifier_status.reason}",
        "",
        "| mode | status | task | precision | recall | f1 | accuracy | TP | FP | FN | TN |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for mode, tasks in comparisons.items():
        for task in ("pii", "injection"):
            metric = tasks[task]
            lines.append(
                f"| {mode} | {statuses[mode]} | {task} | {metric['precision']:.3f} | {metric['recall']:.3f} | "
                f"{metric['f1']:.3f} | {metric['accuracy']:.3f} | {metric['tp']} | {metric['fp']} | "
                f"{metric['fn']} | {metric['tn']} |"
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare regex, rule, model, and hybrid detector baselines."
    )
    parser.add_argument("--dataset", default="evaluation/sample_dataset.json", help="Path to JSON dataset.")
    parser.add_argument(
        "--report",
        default="reports/baseline_compare_report.md",
        help="Output markdown report path.",
    )
    args = parser.parse_args()

    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    classifier_status = get_lightweight_classifier().status()
    comparisons = {
        "Regex Only": _evaluate(dataset, _regex_only),
        "Rule Only": _evaluate(dataset, _rule_only),
        "Lightweight Model Only": _evaluate(dataset, _model_only),
        "Hybrid": _evaluate(dataset, _hybrid),
    }
    statuses = {
        "Regex Only": "available",
        "Rule Only": "available",
        "Lightweight Model Only": (
            "available" if classifier_status.enabled else "unavailable (fallback)"
        ),
        "Hybrid": "available" if classifier_status.enabled else "fallback to regex/rule",
    }
    output_path = _render_report(
        comparisons,
        statuses,
        dataset_path=args.dataset,
        output_path=Path(args.report),
    )
    print(f"Baseline comparison saved to: {output_path}")


if __name__ == "__main__":
    main()
