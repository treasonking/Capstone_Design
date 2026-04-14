from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from backend.app.detection.injection_detector import detect_injection
from backend.app.detection.models import DetectionResult
from backend.app.detection.pii_detector import detect_pii
from evaluation.report_generator import generate_markdown_report


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _evaluate_records(
    records: list[dict[str, Any]],
    detector: Callable[[str], list[DetectionResult]],
) -> dict[str, Any]:
    tp = fp = fn = 0
    false_positive_ids: list[str] = []
    false_negative_ids: list[str] = []

    for row in records:
        sample_id = str(row["id"])
        text = str(row.get("text", ""))
        true_labels = set(row.get("labels", []))
        predicted = {item.reason_code for item in detector(text)}

        row_tp = len(predicted & true_labels)
        row_fp = len(predicted - true_labels)
        row_fn = len(true_labels - predicted)

        tp += row_tp
        fp += row_fp
        fn += row_fn

        if row_fp > 0:
            false_positive_ids.append(sample_id)
        if row_fn > 0:
            false_negative_ids.append(sample_id)

    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_ids": false_positive_ids,
        "false_negative_ids": false_negative_ids,
    }


def run_evaluation(dataset_path: str | Path) -> dict[str, Any]:
    dataset = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    pii_rows = [row for row in dataset if row.get("task") == "pii"]
    inj_rows = [row for row in dataset if row.get("task") == "injection"]

    return {
        "meta": {"dataset_size": len(dataset)},
        "pii": _evaluate_records(pii_rows, detect_pii),
        "injection": _evaluate_records(inj_rows, detect_injection),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate PII/Injection detectors.")
    parser.add_argument(
        "--dataset",
        default="evaluation/sample_dataset.json",
        help="Path to JSON dataset.",
    )
    parser.add_argument(
        "--report",
        default="evaluation/evaluation_report.md",
        help="Output markdown report path.",
    )
    args = parser.parse_args()

    metrics = run_evaluation(args.dataset)
    output = generate_markdown_report(metrics, args.report)

    print("Evaluation completed.")
    print(f"PII F1: {metrics['pii']['f1']:.3f}")
    print(f"Injection F1: {metrics['injection']['f1']:.3f}")
    print(f"Report saved to: {output}")


if __name__ == "__main__":
    main()

