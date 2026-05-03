from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Callable

from backend.app.detection.injection_detector import detect_injection
from backend.app.detection.models import DetectionResult
from backend.app.detection.pii_detector import detect_pii
from evaluation.report_generator import generate_markdown_report


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _metric(tp: int, fp: int, fn: int) -> dict[str, Any]:
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
    }


def _suspected_cause(text: str, labels: set[str]) -> str:
    lowered = text.lower()
    if "PII_ACCOUNT_DETECTED" in labels or any(ch.isdigit() for ch in text):
        return "numeric/account-like boundary"
    if any(term in lowered for term in ("system", "prompt", "hidden", "instruction", "규칙", "정책")):
        return "prompt/rule/policy ambiguity"
    return "detector coverage gap"


def _evaluate_records(
    records: list[dict[str, Any]],
    detector: Callable[[str], list[DetectionResult]],
) -> dict[str, Any]:
    counters = Counter()
    false_positive_ids: list[str] = []
    false_negative_ids: list[str] = []
    false_positives: list[dict[str, Any]] = []
    false_negatives: list[dict[str, Any]] = []
    label_counters: dict[str, Counter[str]] = {}

    for row in records:
        sample_id = str(row["id"])
        text = str(row.get("text", ""))
        true_labels = set(row.get("labels", []))
        predicted = {item.reason_code for item in detector(text)}

        tp_labels = predicted & true_labels
        fp_labels = predicted - true_labels
        fn_labels = true_labels - predicted

        counters.update({"tp": len(tp_labels), "fp": len(fp_labels), "fn": len(fn_labels)})

        for label in true_labels | predicted:
            label_counters.setdefault(label, Counter())
            if label in tp_labels:
                label_counters[label].update({"tp": 1})
            elif label in fp_labels:
                label_counters[label].update({"fp": 1})
            elif label in fn_labels:
                label_counters[label].update({"fn": 1})

        if fp_labels:
            false_positive_ids.append(sample_id)
            false_positives.append(
                {
                    "id": sample_id,
                    "expected": sorted(true_labels),
                    "actual": sorted(predicted),
                    "text_excerpt": text[:120],
                    "suspected_cause": _suspected_cause(text, fp_labels),
                }
            )
        if fn_labels:
            false_negative_ids.append(sample_id)
            false_negatives.append(
                {
                    "id": sample_id,
                    "expected": sorted(true_labels),
                    "actual": sorted(predicted),
                    "text_excerpt": text[:120],
                    "suspected_cause": _suspected_cause(text, fn_labels),
                }
            )

    metric = _metric(counters["tp"], counters["fp"], counters["fn"])
    metric.update(
        {
            "false_positive_ids": false_positive_ids,
            "false_negative_ids": false_negative_ids,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "label_metrics": {
                label: _metric(counts["tp"], counts["fp"], counts["fn"])
                for label, counts in sorted(label_counters.items())
            },
        }
    )
    return metric


def _merge_label_metrics(*sections: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Counter[str]] = {}
    for section in sections:
        for label, metric in section.get("label_metrics", {}).items():
            merged.setdefault(label, Counter())
            merged[label].update({"tp": metric["tp"], "fp": metric["fp"], "fn": metric["fn"]})
    return {label: _metric(counts["tp"], counts["fp"], counts["fn"]) for label, counts in sorted(merged.items())}


def run_evaluation(dataset_path: str | Path) -> dict[str, Any]:
    dataset = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    pii_rows = [row for row in dataset if row.get("task") == "pii"]
    inj_rows = [row for row in dataset if row.get("task") == "injection"]

    pii = _evaluate_records(pii_rows, detect_pii)
    injection = _evaluate_records(inj_rows, detect_injection)
    reason_code_metrics = _merge_label_metrics(pii, injection)
    return {
        "meta": {"dataset_size": len(dataset), "dataset": str(dataset_path)},
        "pii": pii,
        "injection": injection,
        "reason_code_metrics": reason_code_metrics,
        "focused_risk_areas": {
            "INJ_OBFUSCATED_INJECTION_ATTEMPT": reason_code_metrics.get("INJ_OBFUSCATED_INJECTION_ATTEMPT", _metric(0, 0, 0)),
            "PII_ACCOUNT_DETECTED": reason_code_metrics.get("PII_ACCOUNT_DETECTED", _metric(0, 0, 0)),
        },
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
