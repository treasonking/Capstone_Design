from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.detection.injection_detector import detect_injection
from backend.app.detection.pii_detector import detect_pii
from scripts.dataset_common import VALID_LABELS, counter_to_dict, labels_for_task, load_dataset


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _f1(precision: float, recall: float) -> float:
    return _safe_div(2 * precision * recall, precision + recall)


def _metric(tp: int, fp: int, fn: int) -> dict[str, Any]:
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": _f1(precision, recall),
    }


def _predict(task: str, text: str) -> set[str]:
    if task == "pii":
        return {item.reason_code for item in detect_pii(text)}
    if task == "injection":
        return {item.reason_code for item in detect_injection(text)}
    return set()


def _comment(text: str, expected: set[str], predicted: set[str]) -> str:
    lower = text.lower()
    if any(term in lower for term in ("system", "prompt", "policy", "rule", "규칙", "정책")):
        return "prompt/rule/policy ambiguity"
    if any(term in lower for term in ("hidden", "instruction", "지시", "필터", "디버그", "debug")):
        return "injection phrase coverage gap"
    if "계좌" in text or any(ch.isdigit() for ch in text):
        return "numeric/account-like boundary"
    if expected - predicted:
        return "missing detector coverage"
    if predicted - expected:
        return "over-matching detector rule"
    return ""


def evaluate(path: str | Path) -> dict[str, Any]:
    rows = load_dataset(path)
    overall = Counter()
    task_metrics: dict[str, Counter[str]] = {"pii": Counter(), "injection": Counter()}
    label_metrics: dict[str, Counter[str]] = {label: Counter() for label in sorted(VALID_LABELS)}
    difficulty_metrics: dict[str, Counter[str]] = {}
    category_metrics: dict[str, Counter[str]] = {}
    false_positives: list[dict[str, Any]] = []
    false_negatives: list[dict[str, Any]] = []

    for row in rows:
        sample_id = str(row["id"])
        task = str(row["task"])
        text = str(row["text"])
        expected = set(row.get("labels", []))
        predicted = _predict(task, text)
        labels_to_score = labels_for_task(task)

        tp_labels = expected & predicted
        fp_labels = predicted - expected
        fn_labels = expected - predicted

        counts = {"tp": len(tp_labels), "fp": len(fp_labels), "fn": len(fn_labels)}
        overall.update(counts)
        task_metrics.setdefault(task, Counter()).update(counts)

        difficulty = str(row.get("difficulty", "<missing>"))
        category = str(row.get("category", "<missing>"))
        difficulty_metrics.setdefault(difficulty, Counter()).update(counts)
        category_metrics.setdefault(category, Counter()).update(counts)

        for label in labels_to_score:
            if label in expected and label in predicted:
                label_metrics[label].update({"tp": 1})
            elif label in expected:
                label_metrics[label].update({"fn": 1})
            elif label in predicted:
                label_metrics[label].update({"fp": 1})

        if fp_labels:
            false_positives.append(
                {
                    "id": sample_id,
                    "task": task,
                    "text": text,
                    "expected": sorted(expected),
                    "predicted": sorted(predicted),
                    "false_positive_labels": sorted(fp_labels),
                    "comment": _comment(text, expected, predicted),
                }
            )
        if fn_labels:
            false_negatives.append(
                {
                    "id": sample_id,
                    "task": task,
                    "text": text,
                    "expected": sorted(expected),
                    "predicted": sorted(predicted),
                    "false_negative_labels": sorted(fn_labels),
                    "comment": _comment(text, expected, predicted),
                }
            )

    label_metric_values = {label: _metric(counts["tp"], counts["fp"], counts["fn"]) for label, counts in label_metrics.items()}
    macro_values = [value for value in label_metric_values.values() if value["tp"] or value["fp"] or value["fn"]]
    macro_precision = _safe_div(sum(item["precision"] for item in macro_values), len(macro_values))
    macro_recall = _safe_div(sum(item["recall"] for item in macro_values), len(macro_values))

    return {
        "meta": {
            "dataset": str(path),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "dataset_size": len(rows),
        },
        "overall_micro": _metric(overall["tp"], overall["fp"], overall["fn"]),
        "overall_macro": {
            "precision": macro_precision,
            "recall": macro_recall,
            "f1": _f1(macro_precision, macro_recall),
        },
        "task_metrics": {task: _metric(counts["tp"], counts["fp"], counts["fn"]) for task, counts in task_metrics.items()},
        "label_metrics": label_metric_values,
        "difficulty_metrics": {key: _metric(value["tp"], value["fp"], value["fn"]) for key, value in difficulty_metrics.items()},
        "category_metrics": {key: _metric(value["tp"], value["fp"], value["fn"]) for key, value in category_metrics.items()},
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def _metric_line(name: str, metric: dict[str, Any]) -> str:
    return (
        f"| {name} | {metric.get('precision', 0):.3f} | {metric.get('recall', 0):.3f} | "
        f"{metric.get('f1', 0):.3f} | {metric.get('tp', '-')} | {metric.get('fp', '-')} | {metric.get('fn', '-')} |"
    )


def write_markdown(result: dict[str, Any], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Detection Evaluation Report",
        "",
        f"- Dataset: `{result['meta']['dataset']}`",
        f"- Generated at: {result['meta']['generated_at']}",
        f"- Dataset size: {result['meta']['dataset_size']}",
        "",
        "## Overall",
        "",
        "| Scope | Precision | Recall | F1 | TP | FP | FN |",
        "|---|---:|---:|---:|---:|---:|---:|",
        _metric_line("micro", result["overall_micro"]),
        f"| macro | {result['overall_macro']['precision']:.3f} | {result['overall_macro']['recall']:.3f} | {result['overall_macro']['f1']:.3f} | - | - | - |",
        "",
        "## Task Metrics",
        "",
        "| Task | Precision | Recall | F1 | TP | FP | FN |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(_metric_line(task, metric) for task, metric in sorted(result["task_metrics"].items()))
    lines.extend(["", "## Label Metrics", "", "| Label | Precision | Recall | F1 | TP | FP | FN |", "|---|---:|---:|---:|---:|---:|---:|"])
    lines.extend(_metric_line(label, metric) for label, metric in sorted(result["label_metrics"].items()) if metric["tp"] or metric["fp"] or metric["fn"])
    lines.extend(["", "## Category Metrics", "", "| Category | Precision | Recall | F1 | TP | FP | FN |", "|---|---:|---:|---:|---:|---:|---:|"])
    lines.extend(_metric_line(category, metric) for category, metric in sorted(result["category_metrics"].items()))
    lines.extend(
        [
            "",
            "## Error Summary",
            "",
            f"- False positive samples: **{len(result['false_positives'])}**",
            f"- False negative samples: **{len(result['false_negatives'])}**",
            "",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def write_error_cases(result: dict[str, Any], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Detection Error Cases", ""]
    for title, key in (("False Positives", "false_positives"), ("False Negatives", "false_negatives")):
        lines.extend([f"## {title}", ""])
        if not result[key]:
            lines.extend(["No cases.", ""])
            continue
        for item in result[key]:
            lines.extend(
                [
                    f"### {item['id']}",
                    "",
                    f"- Task: `{item['task']}`",
                    f"- Text: {item['text']}",
                    f"- Expected: `{item['expected']}`",
                    f"- Predicted: `{item['predicted']}`",
                    f"- Comment: {item['comment']}",
                    "",
                ]
            )
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate detection dataset with task and label metrics.")
    parser.add_argument("--dataset", default="datasets/sample_dataset_v2.json")
    parser.add_argument("--markdown-output", default="reports/detection_eval_report.md")
    parser.add_argument("--json-output", default="reports/detection_eval_report.json")
    parser.add_argument("--errors-output", default="reports/detection_error_cases.md")
    args = parser.parse_args()

    result = evaluate(args.dataset)
    json_output = Path(args.json_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_output = write_markdown(result, args.markdown_output)
    err_output = write_error_cases(result, args.errors_output)

    print(f"Micro F1: {result['overall_micro']['f1']:.3f}")
    print(f"Macro F1: {result['overall_macro']['f1']:.3f}")
    print(f"Report saved to: {md_output}")
    print(f"JSON saved to: {json_output}")
    print(f"Errors saved to: {err_output}")


if __name__ == "__main__":
    main()
