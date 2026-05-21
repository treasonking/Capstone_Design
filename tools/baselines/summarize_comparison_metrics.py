"""Summarize coverage-aware baseline metrics and write paper-ready reports."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Metrics:
    total: int
    tp: int
    fp: int
    tn: int
    fn: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    auroc: float | None = None


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def safe_div(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def compute_auroc(labels: list[int], scores: list[float]) -> float | None:
    positive_scores = [score for label, score in zip(labels, scores) if label == 1]
    negative_scores = [score for label, score in zip(labels, scores) if label == 0]
    if not positive_scores or not negative_scores:
        return None

    wins = 0.0
    for pos_score in positive_scores:
        for neg_score in negative_scores:
            if pos_score > neg_score:
                wins += 1.0
            elif pos_score == neg_score:
                wins += 0.5
    return wins / (len(positive_scores) * len(negative_scores))


def binary_metrics(
    rows: list[dict[str, str]],
    *,
    score_column: str | None = None,
    invert_score: bool = False,
) -> Metrics:
    labels = [int(row["label"]) for row in rows]
    predictions = [int(row["prediction"]) for row in rows]
    tp = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 1)
    fp = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 1)
    tn = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 0)
    fn = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 0)
    total = len(rows)
    accuracy = safe_div(tp + tn, total)
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)

    auroc: float | None = None
    if score_column is not None and rows:
        scores = [float(row[score_column]) for row in rows]
        attack_scores = [-score for score in scores] if invert_score else scores
        auroc = compute_auroc(labels, attack_scores)

    return Metrics(
        total=total,
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1=f1,
        auroc=auroc,
    )


def fmt(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def dataset_summary(dataset_rows: list[dict[str, str]]) -> dict[str, int]:
    labels = [int(row["label"]) for row in dataset_rows]
    return {
        "total": len(dataset_rows),
        "attack": sum(1 for label in labels if label == 1),
        "benign": sum(1 for label in labels if label == 0),
    }


def classify_error(error: str) -> str:
    lowered = error.lower()
    if "timeout" in lowered or "timed out" in lowered:
        return "timeout"
    if "could not parse" in lowered or "parse" in lowered or "json" in lowered:
        return "parse"
    if (
        "runtime" in lowered
        or "traceback" in lowered
        or "modulenotfounderror" in lowered
        or "unicodeencodeerror" in lowered
        or "setup failed" in lowered
        or "returncode" in lowered
    ):
        return "model/runtime"
    return "other"


def write_error_analysis(
    path: Path,
    error_rows: list[dict[str, str]],
    dataset_rows: list[dict[str, str]],
) -> None:
    dataset_by_id = {row["id"]: row for row in dataset_rows}
    counts = Counter(classify_error(row.get("error", "")) for row in error_rows)
    top_rows = error_rows[:10]
    representative = next((row for row in error_rows if row.get("query_preview")), None)
    if representative is None and error_rows:
        representative = error_rows[0]

    representative_error = ""
    top_lines = "\n".join(
        f"| {row.get('id', '')} | {row.get('label', '')} | {classify_error(row.get('error', ''))} |"
        for row in top_rows
    )
    preview = ""
    if representative is not None:
        representative_error = representative.get("error", "").replace("\n", " ")[:1000]
        preview = representative.get("query_preview", "")
        if not preview and representative.get("id") in dataset_by_id:
            preview = dataset_by_id[representative["id"]].get("text", "")
    preview = preview.replace("\n", " ")[:1000]

    content = f"""# Attention Tracker Error Analysis

## Summary

| Error type | Count |
|---|---:|
| Total errors | {len(error_rows)} |
| Timeout errors | {counts.get("timeout", 0)} |
| Parse errors | {counts.get("parse", 0)} |
| Model/runtime errors | {counts.get("model/runtime", 0)} |
| Other errors | {counts.get("other", 0)} |

## Top 10 Failed IDs

| ID | Label | Classified reason |
|---|---:|---|
{top_lines}

## Representative Failed Query Preview

{preview if preview else "N/A"}

## Representative Error Message

{representative_error if representative_error else "N/A"}
"""
    path.write_text(content, encoding="utf-8")


def write_attention_report(
    path: Path,
    metrics: Metrics,
    error_count: int,
    dataset_rows: list[dict[str, str]],
    threshold: float,
) -> None:
    summary = dataset_summary(dataset_rows)
    content = f"""# Attention Tracker Baseline Report

## Evaluation Setup

| Item | Value |
|---|---:|
| Dataset source | Capstone GitHub dataset, deepset rows from `datasets/external_splits/` |
| Shared evaluation file | `data/external/attention_tracker/shared_prompt_injection_eval.csv` |
| Shared dataset rows | {summary["total"]} |
| Attack samples in shared dataset | {summary["attack"]} |
| Benign samples in shared dataset | {summary["benign"]} |
| Successful Attention Tracker rows | {metrics.total} |
| Error rows | {error_count} |
| Focus-score threshold | {threshold:.4f} |

## Metrics

| Metric | Value |
|---|---:|
| Accuracy | {fmt(metrics.accuracy)} |
| Precision | {fmt(metrics.precision)} |
| Recall | {fmt(metrics.recall)} |
| F1 | {fmt(metrics.f1)} |
| AUROC using inverted score | {fmt(metrics.auroc)} |

## Confusion Matrix

|  | Predicted Benign | Predicted Attack |
|---|---:|---:|
| Actual Benign | {metrics.tn} | {metrics.fp} |
| Actual Attack | {metrics.fn} | {metrics.tp} |

## Notes

Attention Tracker local metrics are computed only on successfully evaluated rows.

Attention Tracker outputs a focus score where lower scores indicate higher prompt injection likelihood. AUROC is computed with `attack_score = -focus_score`.

Attention Tracker's local reproduction result is computed on the capstone-selected evaluation dataset or subset. It is not identical to the paper's original full evaluation setting.
"""
    path.write_text(content, encoding="utf-8")


def write_capstone_report(
    path: Path,
    full_metrics: Metrics,
    matched_metrics: Metrics,
    dataset_rows: list[dict[str, str]],
) -> None:
    summary = dataset_summary(dataset_rows)
    content = f"""# Capstone Detector Baseline Report

## Evaluation Setup

| Item | Value |
|---|---:|
| Dataset source | Capstone GitHub dataset, deepset rows from `datasets/external_splits/` |
| Shared evaluation file | `data/external/attention_tracker/shared_prompt_injection_eval.csv` |
| Shared dataset rows | {summary["total"]} |
| Attack samples in shared dataset | {summary["attack"]} |
| Benign samples in shared dataset | {summary["benign"]} |
| Full capstone rows | {full_metrics.total} |
| Matched capstone rows | {matched_metrics.total} |

## Metrics

| Evaluation scope | Accuracy | Precision | Recall | F1 | AUROC |
|---|---:|---:|---:|---:|---:|
| Full 100 rows | {fmt(full_metrics.accuracy)} | {fmt(full_metrics.precision)} | {fmt(full_metrics.recall)} | {fmt(full_metrics.f1)} | N/A |
| Same successful rows as Attention Tracker | {fmt(matched_metrics.accuracy)} | {fmt(matched_metrics.precision)} | {fmt(matched_metrics.recall)} | {fmt(matched_metrics.f1)} | N/A |

## Prediction Mapping

The capstone detector result is converted to a binary prompt injection prediction from `action` and `reason_codes`.

Rows with injection reason codes such as `INJ_`, `PROMPT_INJECTION`, `JAILBREAK`, `POLICY_BYPASS`, `DIRECT_OVERRIDE`, `SYSTEM_PROMPT`, or `IGNORE_INSTRUCTION` are counted as attack predictions. PII-only reason codes are counted as benign for this prompt injection benchmark.
"""
    path.write_text(content, encoding="utf-8")


def write_comparison_table(
    path: Path,
    *,
    dataset_rows: list[dict[str, str]],
    attention_metrics: Metrics,
    attention_error_count: int,
    capstone_full_metrics: Metrics,
    capstone_matched_metrics: Metrics,
) -> None:
    summary = dataset_summary(dataset_rows)
    content = f"""# Paper Baseline Comparison

## Dataset Coverage

| Method | Evaluation scope | Input rows | Result rows | Error count |
|---|---|---:|---:|---:|
| Attention Tracker | Capstone selected dataset | {summary["total"]} | {attention_metrics.total} | {attention_error_count} |
| Our Capstone Hybrid Proxy | Full capstone selected dataset | {summary["total"]} | {capstone_full_metrics.total} | 0 |
| Our Capstone Hybrid Proxy | Matched with Attention Tracker successful rows | {attention_metrics.total} | {capstone_matched_metrics.total} | 0 |

## Quantitative Results

| Method | Evaluation scope | Accuracy | Precision | Recall | F1 | AUROC |
|---|---|---:|---:|---:|---:|---:|
| Attention Tracker | Successful rows only | {fmt(attention_metrics.accuracy)} | {fmt(attention_metrics.precision)} | {fmt(attention_metrics.recall)} | {fmt(attention_metrics.f1)} | {fmt(attention_metrics.auroc)} |
| Our Capstone Hybrid Proxy | Same successful rows as Attention Tracker | {fmt(capstone_matched_metrics.accuracy)} | {fmt(capstone_matched_metrics.precision)} | {fmt(capstone_matched_metrics.recall)} | {fmt(capstone_matched_metrics.f1)} | N/A |
| Our Capstone Hybrid Proxy | Full 100 rows | {fmt(capstone_full_metrics.accuracy)} | {fmt(capstone_full_metrics.precision)} | {fmt(capstone_full_metrics.recall)} | {fmt(capstone_full_metrics.f1)} | N/A |
| Attention Tracker | Paper-reported deepset | N/A | N/A | N/A | N/A | 0.98 |

## Interpretation

Attention Tracker local metrics are computed only on successfully evaluated rows.

Because 25 out of 100 rows initially failed due to local runtime constraints, the 75-row local result must not be interpreted as full-dataset performance.

Our Capstone Hybrid Proxy is additionally evaluated on the full 100-row selected dataset.

The matched subset comparison is included only for method-to-method comparison under identical row coverage.

Attention Tracker's paper-reported AUROC 0.98 is not a local reproduction result.

The local Attention Tracker AUROC {fmt(attention_metrics.auroc)} uses inverted focus scores: `attack_score = -focus_score`.

Our Capstone Hybrid Proxy's matched deepset subset F1 {fmt(capstone_matched_metrics.f1)} is an external baseline result showing limitations on English public prompt-injection datasets. The full 100-row deepset subset F1 is {fmt(capstone_full_metrics.f1)}. These results should be interpreted separately from the project's internal public-sector and PII-specialized evaluation results.
"""
    path.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attention-csv", required=True)
    parser.add_argument("--attention-error-csv", required=True)
    parser.add_argument("--capstone-full-csv", required=True)
    parser.add_argument("--capstone-matched-csv", required=True)
    parser.add_argument("--dataset-csv", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--threshold", type=float, default=0.12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_rows = read_rows(Path(args.dataset_csv))
    attention_rows = read_rows(Path(args.attention_csv))
    attention_error_rows = read_rows(Path(args.attention_error_csv))
    capstone_full_rows = read_rows(Path(args.capstone_full_csv))
    capstone_matched_rows = read_rows(Path(args.capstone_matched_csv))

    dataset_count = len(dataset_rows)
    attention_error_count = max(dataset_count - len(attention_rows), len(attention_error_rows))
    attention_metrics = binary_metrics(
        attention_rows,
        score_column="score",
        invert_score=True,
    )
    capstone_full_metrics = binary_metrics(capstone_full_rows)
    capstone_matched_metrics = binary_metrics(capstone_matched_rows)

    output_path = Path(args.output_md)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_dir = output_path.parent
    write_attention_report(
        report_dir / "attention_tracker_report.md",
        attention_metrics,
        attention_error_count,
        dataset_rows,
        args.threshold,
    )
    write_capstone_report(
        report_dir / "capstone_detector_report.md",
        capstone_full_metrics,
        capstone_matched_metrics,
        dataset_rows,
    )
    write_error_analysis(
        report_dir / "attention_tracker_error_analysis.md",
        attention_error_rows,
        dataset_rows,
    )
    write_comparison_table(
        output_path,
        dataset_rows=dataset_rows,
        attention_metrics=attention_metrics,
        attention_error_count=attention_error_count,
        capstone_full_metrics=capstone_full_metrics,
        capstone_matched_metrics=capstone_matched_metrics,
    )

    print(f"attention_rows={attention_metrics.total} attention_errors={attention_error_count}")
    print(f"capstone_full_rows={capstone_full_metrics.total}")
    print(f"capstone_matched_rows={capstone_matched_metrics.total}")
    print(f"output={output_path}")


if __name__ == "__main__":
    main()
