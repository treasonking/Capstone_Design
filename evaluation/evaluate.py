from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Callable

from backend.app.detection.hybrid_detector import detect_hybrid_detections
from backend.app.detection.models import DetectionResult
from backend.app.detection.models import DetectorType
from backend.app.engine.policy_engine import evaluate_policy
from backend.app.services.proxy_service import POLICY_PATH
from evaluation.report_generator import generate_markdown_report


_CANONICAL_REASON_CODES = {
    "INJ_POLICY_BYPASS": "INJ_POLICY_BYPASS_ATTEMPT",
    "INJ_DIRECT_OVERRIDE": "INJ_DIRECT_OVERRIDE_ATTEMPT",
}


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
        true_labels = {_CANONICAL_REASON_CODES.get(label, label) for label in row.get("labels", [])}
        predicted = {_CANONICAL_REASON_CODES.get(item.reason_code, item.reason_code) for item in detector(text)}

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


def _evaluate_hybrid_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    passed = 0
    failed = 0

    for row in records:
        text = str(row.get("text", ""))
        expected_action = str(row.get("expected_action", "ALLOW"))
        expected_reasons = set(row.get("expected_reasons", []))
        expected_pii = bool(row.get("expected_pii_detected", False))
        expected_injection = bool(row.get("expected_injection_detected", False))

        hybrid = detect_hybrid_detections(text)
        decision = evaluate_policy(text, hybrid, POLICY_PATH)
        actual_reasons = set(decision.reasons)
        actual_action = decision.final_action.value
        actual_pii = any(item.detector_type == DetectorType.PII for item in hybrid)
        actual_injection = any(item.detector_type == DetectorType.INJECTION for item in hybrid)

        is_pass = (
            actual_action == expected_action
            and expected_reasons.issubset(actual_reasons)
            and actual_pii == expected_pii
            and actual_injection == expected_injection
        )
        if is_pass:
            passed += 1
        else:
            failed += 1

        cases.append(
            {
                "id": str(row.get("id", "")),
                "text": text,
                "expected_action": expected_action,
                "actual_action": actual_action,
                "expected_reasons": sorted(expected_reasons),
                "actual_reasons": sorted(actual_reasons),
                "result": "PASS" if is_pass else "FAIL",
            }
        )

    return {
        "total": len(records),
        "passed": passed,
        "failed": failed,
        "cases": cases,
    }


def run_evaluation(dataset_path: str | Path) -> dict[str, Any]:
    dataset = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    pii_rows = [row for row in dataset if row.get("task") == "pii"]
    inj_rows = [row for row in dataset if row.get("task") == "injection"]
    hybrid_rows = [row for row in dataset if row.get("task") == "hybrid"]

    pii = _evaluate_records(
        pii_rows,
        lambda text: [item for item in detect_hybrid_detections(text) if item.detector_type == DetectorType.PII],
    )
    injection = _evaluate_records(
        inj_rows,
        lambda text: [item for item in detect_hybrid_detections(text) if item.detector_type == DetectorType.INJECTION],
    )
    reason_code_metrics = _merge_label_metrics(pii, injection)
    return {
        "meta": {"dataset_size": len(dataset), "dataset": str(dataset_path)},
        "pii": pii,
        "injection": injection,
        "hybrid": _evaluate_hybrid_records(hybrid_rows),
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
        default="reports/evaluation_report.md",
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
