"""Summarize multi-dataset external baseline evaluation artifacts."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


DATASET_KEYS = ["deepset", "protectai", "lakera"]
DISPLAY_NAMES = {
    "deepset": "deepset",
    "protectai": "ProtectAI",
    "lakera": "Lakera",
}
DEFAULT_INPUT_DIR = Path("reports/baselines/multi_dataset")
PENDING_BASELINES = [
    (
        "PIGuard",
        "Main paper comparison target",
        "`leolee99/PIGuard`; official code `https://github.com/leolee99/PIGuard`",
    ),
    (
        "Meta Prompt Guard 2",
        "Execution baseline",
        "`meta-llama/Llama-Prompt-Guard-2-86M`",
    ),
    (
        "ProtectAI detector",
        "Execution baseline",
        "`protectai/deberta-v3-base-prompt-injection`; fallback `protectai/deberta-v3-small-prompt-injection-v2`",
    ),
]


@dataclass(frozen=True, slots=True)
class Metrics:
    total: int
    accuracy: float | None
    precision: float | None
    recall: float | None
    f1: float | None
    auroc: float | None


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_lines_lf(path: Path, lines: list[str]) -> None:
    path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


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
    if not rows:
        return Metrics(0, None, None, None, None, None)

    labels = [int(row["label"]) for row in rows]
    predictions = [int(row["prediction"]) for row in rows]
    tp = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 1)
    fp = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 1)
    tn = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 0)
    fn = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 0)

    accuracy = safe_div(tp + tn, len(rows))
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)
    auroc: float | None = None
    if score_column is not None:
        scores = [float(row[score_column]) for row in rows]
        attack_scores = [-score for score in scores] if invert_score else scores
        auroc = compute_auroc(labels, attack_scores)

    return Metrics(len(rows), accuracy, precision, recall, f1, auroc)


def fmt(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def dataset_label_counts(rows: list[dict[str, str]]) -> tuple[int, int]:
    attacks = sum(1 for row in rows if int(row["label"]) == 1)
    benign = sum(1 for row in rows if int(row["label"]) == 0)
    return attacks, benign


def attention_note(dataset_key: str, rows: list[dict[str, str]], errors: list[dict[str, str]]) -> str:
    if rows:
        return "Local metrics use successfully evaluated rows only; AUROC uses inverted focus score."
    if errors and "Local runtime dependency missing" in errors[0].get("error", ""):
        return "Local runtime dependency missing in Codex environment; do not count as performance result."
    if errors:
        return "No successful Attention Tracker rows; do not count as performance result."
    return "No Attention Tracker output available."


def capstone_full_note(dataset_key: str, dataset_rows: list[dict[str, str]]) -> str:
    _, benign = dataset_label_counts(dataset_rows)
    if dataset_key == "lakera" or benign == 0:
        return (
            "Lakera subset is attack-only and should be interpreted as attack recall stress test, "
            "not balanced binary classification. Precision is limited because no benign rows exist."
        )
    return "Capstone detector result on the full local selected dataset."


def capstone_matched_note(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "No Attention Tracker successful rows; matched comparison is not available."
    return "Same row coverage as the historical Attention Tracker successful-row subset."


def coverage_rows(input_dir: Path) -> list[str]:
    lines = [
        "# Multi-Dataset External Baseline Coverage",
        "",
        "This coverage summary supports comparison baseline selection and execution pipeline preparation. It is not a final PIGuard / Prompt Guard 2 / ProtectAI detector performance result.",
        "",
        "| Dataset | Method | Evaluation scope | Input rows | Result rows | Error count |",
        "|---|---|---|---:|---:|---:|",
    ]
    for dataset_key in DATASET_KEYS:
        name = DISPLAY_NAMES[dataset_key]
        dataset_rows = read_rows(input_dir / f"{dataset_key}_shared_eval.csv")
        attention_rows = read_rows(input_dir / f"{dataset_key}_attention_tracker_results.csv")
        attention_errors = read_rows(input_dir / f"{dataset_key}_attention_tracker_errors.csv")
        capstone_full = read_rows(input_dir / f"{dataset_key}_capstone_results_full.csv")
        capstone_matched = read_rows(input_dir / f"{dataset_key}_capstone_results_matched.csv")
        attention_error_count = max(len(dataset_rows) - len(attention_rows), len(attention_errors))

        lines.extend(
            [
                f"| {name} | Shared dataset | Common-format input | {len(dataset_rows)} | {len(dataset_rows)} | 0 |",
                f"| {name} | Capstone Hybrid Proxy | Local full evaluation | {len(dataset_rows)} | {len(capstone_full)} | 0 |",
                f"| {name} | Capstone Hybrid Proxy | Matched with Attention Tracker successful rows | {len(attention_rows)} | {len(capstone_matched)} | 0 |",
                f"| {name} | Attention Tracker | Related-work local attempt, excluded from main comparison | {len(dataset_rows)} | {len(attention_rows)} | {attention_error_count} |",
                f"| {name} | PIGuard | Pending / Not measured | {len(dataset_rows)} | 0 | {len(dataset_rows)} |",
                f"| {name} | Meta Prompt Guard 2 | Pending / Not measured | {len(dataset_rows)} | 0 | {len(dataset_rows)} |",
                f"| {name} | ProtectAI detector | Pending / Not measured | {len(dataset_rows)} | 0 | {len(dataset_rows)} |",
            ]
        )
    return lines


def quantitative_lines(input_dir: Path) -> list[str]:
    lines = [
        "# Multi-Dataset External Baseline Evaluation",
        "",
        "This table records comparison baseline selection and execution pipeline preparation. Capstone Hybrid Proxy has local full evaluation results. PIGuard, Meta Prompt Guard 2, and ProtectAI detector are selected baselines but remain Pending / Not measured until their models are executed on the shared CSV inputs.",
        "",
        "Attention Tracker is excluded from the main local comparison and retained only as related work with paper-reported AUROC reference values.",
        "",
        "| Dataset | Method | Result type | Evaluation scope | Rows | Accuracy | Precision | Recall | F1 | AUROC | Notes |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for dataset_key in DATASET_KEYS:
        name = DISPLAY_NAMES[dataset_key]
        dataset_rows = read_rows(input_dir / f"{dataset_key}_shared_eval.csv")
        attention_rows = read_rows(input_dir / f"{dataset_key}_attention_tracker_results.csv")
        capstone_matched_rows = read_rows(input_dir / f"{dataset_key}_capstone_results_matched.csv")
        capstone_full_rows = read_rows(input_dir / f"{dataset_key}_capstone_results_full.csv")
        capstone_matched = binary_metrics(capstone_matched_rows)
        capstone_full = binary_metrics(capstone_full_rows)
        lines.extend(
            [
                f"| {name} | Capstone Hybrid Proxy | Full | Local full evaluation | {capstone_full.total} | {fmt(capstone_full.accuracy)} | {fmt(capstone_full.precision)} | {fmt(capstone_full.recall)} | {fmt(capstone_full.f1)} | N/A | {capstone_full_note(dataset_key, dataset_rows)} |",
                f"| {name} | Capstone Hybrid Proxy | Matched | Same rows as Attention Tracker successful local attempt | {capstone_matched.total} | {fmt(capstone_matched.accuracy)} | {fmt(capstone_matched.precision)} | {fmt(capstone_matched.recall)} | {fmt(capstone_matched.f1)} | N/A | {capstone_matched_note(capstone_matched_rows)} |",
            ]
        )
        for method, role, source in PENDING_BASELINES:
            lines.append(
                f"| {name} | {method} | Not executed | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | {role}; selected source {source}. |"
            )
    lines.append(
        "| deepset | Attention Tracker | Paper-reported | Related work only | N/A | N/A | N/A | N/A | N/A | 0.98 | Original paper Qwen2 1.5B result; not a local reproduction result and not part of the main local comparison. |"
    )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Capstone Hybrid Proxy is reported as local full evaluation on the three shared datasets. Matched rows are included only to preserve compatibility with the historical Attention Tracker reproduction artifacts.",
            "",
            "PIGuard is the main paper comparison target. Meta Prompt Guard 2 and ProtectAI detector are executable baselines. They are Pending / Not measured until their HuggingFace models are run on the shared CSV inputs.",
            "",
            "Attention Tracker is discussed only as related work here. Its paper-reported deepset AUROC 0.98 is not a local reproduction result.",
            "",
            "Lakera subset is attack-only and should be interpreted as attack recall stress test, not balanced binary classification.",
        ]
    )
    return lines


def runtime_failure_notes(input_dir: Path) -> list[str]:
    notes: list[str] = []
    for dataset_key in DATASET_KEYS:
        errors = read_rows(input_dir / f"{dataset_key}_attention_tracker_errors.csv")
        if not errors:
            continue
        first_error = errors[0].get("error", "")
        if "Local runtime dependency missing" in first_error or "No module named 'torch'" in first_error:
            notes.append(
                f"- {DISPLAY_NAMES[dataset_key]} Attention Tracker local metrics were not executed because local runtime dependencies are missing in the Codex environment. This is not a performance result."
            )
    return notes


def readme_summary(input_dir: Path) -> list[str]:
    lines = [
        "## Multi-Dataset External Baseline Summary",
        "",
        "This section summarizes comparison baseline selection and execution pipeline preparation for three external prompt-injection datasets: deepset, ProtectAI, and Lakera.",
        "",
        "Capstone Hybrid Proxy has local full evaluation results. PIGuard is the main paper comparison target, while Meta Prompt Guard 2 and ProtectAI detector are selected executable baselines. PIGuard / Meta Prompt Guard 2 / ProtectAI detector remain Pending / Not measured until their models are executed on the shared CSV inputs.",
        "",
        "Attention Tracker is excluded from the main local comparison and kept only as related work with paper-reported AUROC reference values.",
        "",
        "### Prepared Inputs",
        "",
        "| Dataset | Rows | Attack rows | Benign rows | Common-format file |",
        "|---|---:|---:|---:|---|",
    ]
    for dataset_key in DATASET_KEYS:
        name = DISPLAY_NAMES[dataset_key]
        dataset_rows = read_rows(input_dir / f"{dataset_key}_shared_eval.csv")
        attacks, benign = dataset_label_counts(dataset_rows)
        lines.append(
            f"| {name} | {len(dataset_rows)} | {attacks} | {benign} | `reports/baselines/multi_dataset/{dataset_key}_shared_eval.csv` |"
        )

    lines.extend(
        [
            "",
            "### Capstone Hybrid Proxy Local Full Evaluation",
            "",
            "| Dataset | Rows | Accuracy | Precision | Recall | F1 | Notes |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for dataset_key in DATASET_KEYS:
        name = DISPLAY_NAMES[dataset_key]
        dataset_rows = read_rows(input_dir / f"{dataset_key}_shared_eval.csv")
        capstone_full = read_rows(input_dir / f"{dataset_key}_capstone_results_full.csv")
        metrics = binary_metrics(capstone_full)
        lines.append(
            f"| {name} | {metrics.total} | {fmt(metrics.accuracy)} | {fmt(metrics.precision)} | {fmt(metrics.recall)} | {fmt(metrics.f1)} | {capstone_full_note(dataset_key, dataset_rows)} |"
        )

    lines.extend(
        [
            "",
            "### Pending / Not Measured Baselines",
            "",
            "| Method | Role | Status | Source |",
            "|---|---|---|---|",
        ]
    )
    for method, role, source in PENDING_BASELINES:
        lines.append(f"| {method} | {role} | Pending / Not measured | {source} |")

    lines.extend(
        [
            "",
            "### Attention Tracker Related-Work Reference",
            "",
            "| Dataset | Target model | Result type | AUROC | Note |",
            "|---|---|---|---:|---|",
            "| deepset prompt injection | Qwen2 1.5B | Paper-reported | 0.98 | Related-work reference only; not a local reproduction result. |",
            "",
            "### Limitations",
            "",
            "- This update prepares comparison baselines and execution pipeline outputs; it does not claim final PIGuard / Prompt Guard 2 / ProtectAI detector performance.",
            "- Lakera is attack-only in the selected local subset, so interpret it as a recall stress test rather than balanced binary classification.",
            "- Capstone Hybrid Proxy results on external English prompt-injection datasets should be interpreted separately from internal public-sector and PII-focused evaluations.",
        ]
    )
    return lines


def write_dataset_info(input_dir: Path) -> None:
    lines = [
        "# Selected Multi-Dataset Inputs",
        "",
        "| Dataset | Selected rows | Attack rows | Benign rows | Note |",
        "|---|---:|---:|---:|---|",
    ]
    notes = {
        "deepset": "Repository-local selected subset in common prompt-injection format.",
        "protectai": "Balanced subset selected from repository-local external split.",
        "lakera": "Attack-focused dataset; no benign rows available in repository-local split.",
    }
    for dataset_key in DATASET_KEYS:
        rows = read_rows(input_dir / f"{dataset_key}_shared_eval.csv")
        attacks, benign = dataset_label_counts(rows)
        lines.append(
            f"| {DISPLAY_NAMES[dataset_key]} | {len(rows)} | {attacks} | {benign} | {notes[dataset_key]} |"
        )
    write_lines_lf(input_dir / "selected_dataset_summary.md", lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    input_dir.mkdir(parents=True, exist_ok=True)

    write_lines_lf(input_dir / "dataset_coverage_summary.md", coverage_rows(input_dir))
    write_lines_lf(input_dir / "multi_dataset_comparison_table.md", quantitative_lines(input_dir))
    write_lines_lf(input_dir / "readme_baseline_summary.md", readme_summary(input_dir))
    write_dataset_info(input_dir)
    print(f"coverage={input_dir / 'dataset_coverage_summary.md'}")
    print(f"comparison={input_dir / 'multi_dataset_comparison_table.md'}")
    print(f"readme={input_dir / 'readme_baseline_summary.md'}")


if __name__ == "__main__":
    main()
