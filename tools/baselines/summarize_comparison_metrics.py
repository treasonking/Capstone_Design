"""Summarize baseline metrics and write paper-ready comparison reports."""

from __future__ import annotations

import argparse
import csv
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
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def count_error_rows(path: Path) -> int:
    if not path.exists():
        return 0
    return len(read_rows(path))


def safe_div(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


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


def fmt(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def dataset_summary(dataset_rows: list[dict[str, str]]) -> dict[str, int]:
    labels = [int(row["label"]) for row in dataset_rows]
    return {
        "total": len(dataset_rows),
        "attack": sum(1 for label in labels if label == 1),
        "benign": sum(1 for label in labels if label == 0),
    }


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

Attention Tracker outputs a focus score where lower scores indicate higher prompt injection likelihood. AUROC is computed with `attack_score = -focus_score`.

Attention Tracker's local reproduction result is computed on the capstone-selected evaluation dataset or subset. It is not identical to the paper's original full evaluation setting.
"""
    path.write_text(content, encoding="utf-8")


def write_capstone_report(path: Path, metrics: Metrics, dataset_rows: list[dict[str, str]]) -> None:
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
| Evaluated capstone rows | {metrics.total} |

## Metrics

| Metric | Value |
|---|---:|
| Accuracy | {fmt(metrics.accuracy)} |
| Precision | {fmt(metrics.precision)} |
| Recall | {fmt(metrics.recall)} |
| F1 | {fmt(metrics.f1)} |
| AUROC | N/A |

## Confusion Matrix

|  | Predicted Benign | Predicted Attack |
|---|---:|---:|
| Actual Benign | {metrics.tn} | {metrics.fp} |
| Actual Attack | {metrics.fn} | {metrics.tp} |

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
    capstone_metrics: Metrics,
) -> None:
    summary = dataset_summary(dataset_rows)
    scope = "subset-100" if summary["total"] == 100 else "full"
    if attention_error_count:
        scope = f"{scope}; local metrics use {attention_metrics.total} successful Attention Tracker rows"

    content = f"""# Paper Baseline Comparison

## Dataset

| Item | Value |
|---|---:|
| Dataset source | Capstone GitHub dataset (`datasets/external_splits/`, deepset rows) |
| Evaluation file | `data/external/attention_tracker/shared_prompt_injection_eval.csv` |
| Total samples | {summary["total"]} |
| Attack samples | {summary["attack"]} |
| Benign samples | {summary["benign"]} |
| Evaluation scope | {scope} |

## Run Coverage

| Method | Result rows | Error count |
|---|---:|---:|
| Attention Tracker | {attention_metrics.total} | {attention_error_count} |
| Our Capstone Hybrid Proxy | {capstone_metrics.total} | 0 |

## Quantitative Results

| Method | Result Type | Dataset | LLM Internal Access | Black-box API Compatible | PII Detection | Accuracy | Precision | Recall | F1 | AUROC |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|
| Attention Tracker | Local reproduction | Capstone dataset subset | Required | No | No | {fmt(attention_metrics.accuracy)} | {fmt(attention_metrics.precision)} | {fmt(attention_metrics.recall)} | {fmt(attention_metrics.f1)} | {fmt(attention_metrics.auroc)} |
| Attention Tracker | Paper-reported | deepset/prompt-injections | Required | No | No | N/A | N/A | N/A | N/A | 0.98 |
| Our Capstone Hybrid Proxy | Local reproduction | Same as above | Not required | Yes | Yes | {fmt(capstone_metrics.accuracy)} | {fmt(capstone_metrics.precision)} | {fmt(capstone_metrics.recall)} | {fmt(capstone_metrics.f1)} | N/A |

## Interpretation

Attention Tracker is a strong research baseline for prompt injection detection, but it requires access to internal attention scores of the target LLM. This limits direct applicability to black-box LLM API environments.

Our capstone system operates at the proxy layer and does not require access to model internals. It can inspect user input and LLM output, supports PII detection, provides reason codes, and records audit-friendly metadata.

Therefore, Attention Tracker is used as a high-performance research baseline, while the capstone system is evaluated as a deployment-oriented security proxy for public-sector or internal-network environments.

Attention Tracker's local reproduction result is computed on the capstone-selected evaluation dataset or subset. It is not identical to the paper's original full evaluation setting.

The paper-reported AUROC 0.98 refers to Qwen2 1.5B on the deepset prompt injection dataset. Local reproduction metrics are reported separately.

The local Attention Tracker AUROC uses inverted focus scores: `attack_score = -focus_score`.
"""
    path.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attention-csv", required=True)
    parser.add_argument("--attention-error-csv", required=True)
    parser.add_argument("--capstone-csv", required=True)
    parser.add_argument("--dataset-csv", required=True)
    parser.add_argument("--output-md", required=True)
    parser.add_argument("--threshold", type=float, default=0.12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    attention_rows = read_rows(Path(args.attention_csv))
    capstone_rows = read_rows(Path(args.capstone_csv))
    dataset_rows = read_rows(Path(args.dataset_csv))
    attention_error_count = count_error_rows(Path(args.attention_error_csv))

    attention_metrics = binary_metrics(
        attention_rows,
        score_column="score",
        invert_score=True,
    )
    capstone_metrics = binary_metrics(capstone_rows)

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
        capstone_metrics,
        dataset_rows,
    )
    write_comparison_table(
        output_path,
        dataset_rows=dataset_rows,
        attention_metrics=attention_metrics,
        attention_error_count=attention_error_count,
        capstone_metrics=capstone_metrics,
    )

    print(f"attention_rows={attention_metrics.total} attention_errors={attention_error_count}")
    print(f"capstone_rows={capstone_metrics.total}")
    print(f"output={output_path}")


if __name__ == "__main__":
    main()
