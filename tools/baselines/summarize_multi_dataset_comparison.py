"""Summarize historical Attention Tracker and Capstone reproduction artifacts."""

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
    return "Standalone capstone detector result on the full selected dataset."


def capstone_matched_note(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "No Attention Tracker successful rows; matched comparison is not available."
    return "Same row coverage as Attention Tracker local reproduction."


def coverage_rows(input_dir: Path) -> list[str]:
    lines = [
        "# Historical Attention Tracker Dataset Coverage",
        "",
        "> Status: historical reproduction only. Attention Tracker is retained for related-work context, not as the main baseline.",
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
                f"| {name} | Attention Tracker | Attempted selected dataset | {len(dataset_rows)} | {len(attention_rows)} | {attention_error_count} |",
                f"| {name} | Capstone Hybrid Proxy | Full selected dataset | {len(dataset_rows)} | {len(capstone_full)} | 0 |",
                f"| {name} | Capstone Hybrid Proxy | Matched with Attention Tracker successful rows | {len(attention_rows)} | {len(capstone_matched)} | 0 |",
            ]
        )
    return lines


def quantitative_lines(input_dir: Path) -> list[str]:
    lines = [
        "# Historical Attention Tracker Multi-Dataset Reproduction",
        "",
        "> Status: historical reproduction only. This file is no longer the main baseline comparison. Use `reports/baselines/text_guard_comparison_table.md` for the PIGuard / Prompt Guard 2 / ProtectAI detector baseline plan, and `reports/baselines/related_work_attention_tracker.md` for Attention Tracker related-work context.",
        "",
        "| Dataset | Method | Result type | Evaluation scope | Accuracy | Precision | Recall | F1 | AUROC | Notes |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for dataset_key in DATASET_KEYS:
        name = DISPLAY_NAMES[dataset_key]
        dataset_rows = read_rows(input_dir / f"{dataset_key}_shared_eval.csv")
        attention_rows = read_rows(input_dir / f"{dataset_key}_attention_tracker_results.csv")
        attention_errors = read_rows(input_dir / f"{dataset_key}_attention_tracker_errors.csv")
        attention = binary_metrics(
            attention_rows,
            score_column="score",
            invert_score=True,
        )
        capstone_matched_rows = read_rows(input_dir / f"{dataset_key}_capstone_results_matched.csv")
        capstone_full_rows = read_rows(input_dir / f"{dataset_key}_capstone_results_full.csv")
        capstone_matched = binary_metrics(capstone_matched_rows)
        capstone_full = binary_metrics(capstone_full_rows)
        attention_result_type = "Local reproduction" if attention_rows else "Not executed"
        attention_scope = "Successful rows only" if attention_rows else "Attempted selected dataset"
        lines.extend(
            [
                f"| {name} | Attention Tracker | {attention_result_type} | {attention_scope} | {fmt(attention.accuracy)} | {fmt(attention.precision)} | {fmt(attention.recall)} | {fmt(attention.f1)} | {fmt(attention.auroc)} | {attention_note(dataset_key, attention_rows, attention_errors)} |",
                f"| {name} | Capstone Hybrid Proxy | Matched local comparison | Same rows as Attention Tracker | {fmt(capstone_matched.accuracy)} | {fmt(capstone_matched.precision)} | {fmt(capstone_matched.recall)} | {fmt(capstone_matched.f1)} | N/A | {capstone_matched_note(capstone_matched_rows)} |",
                f"| {name} | Capstone Hybrid Proxy | Full capstone evaluation | Full selected dataset | {fmt(capstone_full.accuracy)} | {fmt(capstone_full.precision)} | {fmt(capstone_full.recall)} | {fmt(capstone_full.f1)} | N/A | {capstone_full_note(dataset_key, dataset_rows)} |",
            ]
        )
    lines.append(
        "| deepset | Attention Tracker | Paper-reported | Original paper | N/A | N/A | N/A | N/A | 0.98 | Original paper Qwen2 1.5B result; not a local reproduction result. |"
    )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Attention Tracker local metrics are computed only on successfully evaluated rows. If some rows fail due to local runtime constraints, those rows are excluded from Attention Tracker local metrics and reported separately in the coverage table.",
            "",
            "Capstone Hybrid Proxy is evaluated in two ways: full selected dataset and matched subset. The matched subset is used for fair comparison with Attention Tracker, while the full selected dataset shows standalone detector behavior.",
            "",
            "Attention Tracker's paper-reported AUROC 0.98 is not a local reproduction result. It is the original paper's Qwen2 1.5B result on deepset.",
            "",
            "Attention Tracker AUROC values in local reproduction rows use inverted focus scores: `attack_score = -focus_score`.",
            "",
            "Lakera subset is attack-only and should be interpreted as attack recall stress test, not balanced binary classification.",
        ]
    )
    setup_failures = runtime_failure_notes(input_dir)
    if setup_failures:
        lines.extend(["", "## Local Runtime Notes", ""])
        lines.extend(setup_failures)
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
        "## Historical Attention Tracker Reproduction",
        "",
        "> Status: historical reproduction only. This section is no longer the main baseline comparison. Use `reports/baselines/readme_text_guard_summary.md` for the current PIGuard / Prompt Guard 2 / ProtectAI detector baseline summary.",
        "",
        "This section reports a limited reproduction experiment for a paper baseline, not the main performance claim of this project.",
        "",
        "The experiment compares Attention Tracker with the Capstone Hybrid Proxy on three prompt-injection benchmark sources: deepset, ProtectAI, and Lakera. Attention Tracker requires access to internal attention scores, while the Capstone system runs as a deployment-oriented proxy for PII leakage prevention and prompt-injection blocking.",
        "",
        "Attention Tracker local metrics are computed only on successfully evaluated rows. Failed rows are reported in the coverage table and are not silently counted as full-dataset performance.",
        "",
        "Attention Tracker's paper-reported AUROC 0.98 is listed separately from local reproduction results; it is the original paper's Qwen2 1.5B result on deepset.",
        "",
        "Capstone Hybrid Proxy is evaluated both on the full selected dataset and on the matched subset where Attention Tracker produced a local result. Low recall on English public prompt-injection benchmarks should be interpreted as a limitation analysis, separate from internal public-sector and PII-focused evaluations.",
        "",
        "deepset has a partial Attention Tracker local reproduction. ProtectAI and Lakera are marked as not executed if the Codex/local runtime cannot provide Attention Tracker dependencies, and those rows are not treated as performance results.",
        "",
        "Lakera is attack-only in this selected subset, so it should be read as an attack recall stress test rather than balanced binary classification.",
        "",
        "### Coverage",
        "",
        "| Dataset | Attention Tracker rows | Attention Tracker errors | Capstone full rows | Capstone matched rows |",
        "|---|---:|---:|---:|---:|",
    ]
    for dataset_key in DATASET_KEYS:
        name = DISPLAY_NAMES[dataset_key]
        dataset_rows = read_rows(input_dir / f"{dataset_key}_shared_eval.csv")
        attention_rows = read_rows(input_dir / f"{dataset_key}_attention_tracker_results.csv")
        attention_errors = read_rows(input_dir / f"{dataset_key}_attention_tracker_errors.csv")
        capstone_full = read_rows(input_dir / f"{dataset_key}_capstone_results_full.csv")
        capstone_matched = read_rows(input_dir / f"{dataset_key}_capstone_results_matched.csv")
        error_count = max(len(dataset_rows) - len(attention_rows), len(attention_errors))
        lines.append(
            f"| {name} | {len(attention_rows)} | {error_count} | {len(capstone_full)} | {len(capstone_matched)} |"
        )

    lines.extend(["", "### Quantitative Summary", ""])
    lines.extend(quantitative_lines(input_dir)[2:6 + (len(DATASET_KEYS) * 3)])
    runtime_notes = runtime_failure_notes(input_dir)
    if runtime_notes:
        lines.extend(["", "### Local Runtime Notes", ""])
        lines.extend(runtime_notes)
    return lines


def write_dataset_info(input_dir: Path) -> None:
    lines = [
        "# Selected Multi-Dataset Inputs",
        "",
        "| Dataset | Selected rows | Attack rows | Benign rows | Note |",
        "|---|---:|---:|---:|---|",
    ]
    notes = {
        "deepset": "Preserves prior deepset local Attention Tracker reproduction subset.",
        "protectai": "Balanced subset selected from repository-local external split.",
        "lakera": "Attack-focused dataset; no benign rows available in repository-local split.",
    }
    for dataset_key in DATASET_KEYS:
        rows = read_rows(input_dir / f"{dataset_key}_shared_eval.csv")
        attacks, benign = dataset_label_counts(rows)
        lines.append(
            f"| {DISPLAY_NAMES[dataset_key]} | {len(rows)} | {attacks} | {benign} | {notes[dataset_key]} |"
        )
    (input_dir / "selected_dataset_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    input_dir.mkdir(parents=True, exist_ok=True)

    (input_dir / "dataset_coverage_summary.md").write_text(
        "\n".join(coverage_rows(input_dir)) + "\n",
        encoding="utf-8",
    )
    (input_dir / "multi_dataset_comparison_table.md").write_text(
        "\n".join(quantitative_lines(input_dir)) + "\n",
        encoding="utf-8",
    )
    (input_dir / "readme_baseline_summary.md").write_text(
        "\n".join(readme_summary(input_dir)) + "\n",
        encoding="utf-8",
    )
    write_dataset_info(input_dir)
    print(f"coverage={input_dir / 'dataset_coverage_summary.md'}")
    print(f"comparison={input_dir / 'multi_dataset_comparison_table.md'}")
    print(f"readme={input_dir / 'readme_baseline_summary.md'}")


if __name__ == "__main__":
    main()
