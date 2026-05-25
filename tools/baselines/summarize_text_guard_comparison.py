"""Summarize Capstone and executable text-guard baseline results."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


DATASETS = (
    ("deepset", "deepset", "balanced or selected subset"),
    ("protectai", "ProtectAI", "selected subset"),
    ("lakera", "Lakera", "attack-only recall stress test"),
)
DEFAULT_INPUT_DIR = Path("reports/baselines/multi_dataset")
DEFAULT_OUTPUT_DIR = Path("reports/baselines")
RUNTIME_NOTES = Path("reports/baselines/text_guard_runtime_notes.md")


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


def write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def compute_auroc(labels: list[int], scores: list[float]) -> float | None:
    positives = [score for label, score in zip(labels, scores) if label == 1]
    negatives = [score for label, score in zip(labels, scores) if label == 0]
    if not positives or not negatives:
        return None

    wins = 0.0
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def binary_metrics(rows: list[dict[str, str]], score_column: str | None = None) -> Metrics:
    if not rows:
        return Metrics(0, None, None, None, None, None)

    labels = [int(row["label"]) for row in rows]
    predictions = [int(row["prediction"]) for row in rows]
    tp = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 1)
    fp = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 1)
    tn = sum(1 for label, pred in zip(labels, predictions) if label == 0 and pred == 0)
    fn = sum(1 for label, pred in zip(labels, predictions) if label == 1 and pred == 0)

    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)
    auroc = None
    if score_column and len(set(labels)) == 2:
        scores = [float(row[score_column]) for row in rows]
        auroc = compute_auroc(labels, scores)

    return Metrics(
        total=len(rows),
        accuracy=safe_div(tp + tn, len(rows)),
        precision=precision,
        recall=recall,
        f1=f1,
        auroc=auroc,
    )


def fmt(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.4f}"


def label_counts(rows: list[dict[str, str]]) -> tuple[int, int]:
    attack = sum(1 for row in rows if int(row["label"]) == 1)
    benign = sum(1 for row in rows if int(row["label"]) == 0)
    return attack, benign


def protectai_status(result_rows: list[dict[str, str]], runtime_notes_path: Path) -> str:
    if result_rows:
        return "Local reproduction"
    if runtime_notes_path.exists():
        return "Blocked"
    return "Pending"


def protectai_note(result_rows: list[dict[str, str]], dataset_key: str, runtime_notes_path: Path) -> str:
    if result_rows:
        model_name = result_rows[0].get("model_name", "ProtectAI HuggingFace detector")
        if dataset_key == "lakera":
            return f"HF text classifier `{model_name}`; attack-only recall stress test."
        return f"HF text classifier `{model_name}`."
    if runtime_notes_path.exists():
        return "HF model download/runtime failed; not interpreted as a performance result."
    return "not measured yet"


def comparison_table(input_dir: Path, runtime_notes_path: Path) -> list[str]:
    lines = [
        "# Text Guard Baseline Comparison",
        "",
        "## Dataset Summary",
        "",
        "| Dataset | Rows | Attack | Benign | Notes |",
        "|---|---:|---:|---:|---|",
    ]
    for dataset_key, display_name, note in DATASETS:
        rows = read_rows(input_dir / f"{dataset_key}_shared_eval.csv")
        attack, benign = label_counts(rows)
        lines.append(f"| {display_name} | {len(rows)} | {attack} | {benign} | {note} |")

    lines.extend(
        [
            "",
            "## Quantitative Results",
            "",
            "| Dataset | Method | Result type | Accuracy | Precision | Recall | F1 | AUROC | Notes |",
            "|---|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )

    for dataset_key, display_name, _ in DATASETS:
        capstone_rows = read_rows(input_dir / f"{dataset_key}_capstone_results_full.csv")
        capstone_metrics = binary_metrics(capstone_rows)
        capstone_note = "proxy-level detector"
        if dataset_key == "lakera":
            capstone_note = "attack-only"
        lines.append(
            f"| {display_name} | Capstone Hybrid Proxy | Local full evaluation | "
            f"{fmt(capstone_metrics.accuracy)} | {fmt(capstone_metrics.precision)} | "
            f"{fmt(capstone_metrics.recall)} | {fmt(capstone_metrics.f1)} | N/A | {capstone_note} |"
        )

        protectai_rows = read_rows(input_dir / f"{dataset_key}_protectai_detector_results.csv")
        protectai_metrics = binary_metrics(protectai_rows, score_column="score")
        status = protectai_status(protectai_rows, runtime_notes_path)
        lines.append(
            f"| {display_name} | ProtectAI detector | {status} | "
            f"{fmt(protectai_metrics.accuracy)} | {fmt(protectai_metrics.precision)} | "
            f"{fmt(protectai_metrics.recall)} | {fmt(protectai_metrics.f1)} | "
            f"{fmt(protectai_metrics.auroc)} | {protectai_note(protectai_rows, dataset_key, runtime_notes_path)} |"
        )

        lines.append(
            f"| {display_name} | Meta Prompt Guard 2 | Pending | N/A | N/A | N/A | N/A | N/A | not measured yet |"
        )
        lines.append(
            f"| {display_name} | PIGuard | Pending | N/A | N/A | N/A | N/A | N/A | main paper baseline, not measured yet |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "ProtectAI detector rows marked Local reproduction are executable HuggingFace baseline results produced on the same shared CSV inputs as the Capstone Hybrid Proxy.",
            "",
            "PIGuard remains the main paper-level text-guard comparison target, but no local PIGuard metrics are reported until its official model/code is executed. Meta Prompt Guard 2 is also still pending.",
            "",
            "Attention Tracker is excluded from the main quantitative table and retained only as related work because it requires internal LLM attention access.",
            "",
            "These external prompt-injection datasets are used for generalization analysis, not as the primary project performance benchmark.",
        ]
    )
    return lines


def readme_summary(input_dir: Path, runtime_notes_path: Path) -> list[str]:
    lines = [
        "### External Text-Guard Baseline Evaluation",
        "",
        "We evaluated the Capstone Hybrid Proxy on three external prompt-injection datasets: deepset, ProtectAI, and Lakera. We also added ProtectAI's HuggingFace prompt-injection detector as the first executable text-guard baseline.",
        "",
        "PIGuard is selected as the main paper-level comparison target because it is an input-text-based prompt guard study, while Attention Tracker is retained only as related work due to its requirement for internal LLM attention access.",
        "",
        "Meta Prompt Guard 2 is still an executable baseline candidate, but it has not produced local metrics in this repository yet. PIGuard also remains pending until its official model/code path is executed locally.",
        "",
        "These results should be interpreted as external generalization analysis, not as the primary project performance benchmark. The project target remains proxy-level PII leakage prevention, prompt-injection blocking, reason-code generation, and audit-friendly logging for public-sector or internal-network environments.",
        "",
        "#### Dataset Coverage",
        "",
        "| Dataset | Rows | Attack | Benign | Notes |",
        "|---|---:|---:|---:|---|",
    ]
    for dataset_key, display_name, note in DATASETS:
        rows = read_rows(input_dir / f"{dataset_key}_shared_eval.csv")
        attack, benign = label_counts(rows)
        lines.append(f"| {display_name} | {len(rows)} | {attack} | {benign} | {note} |")

    lines.extend(
        [
            "",
            "#### Local Metrics Snapshot",
            "",
            "| Dataset | Method | Result type | Accuracy | Precision | Recall | F1 | AUROC |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for dataset_key, display_name, _ in DATASETS:
        capstone_rows = read_rows(input_dir / f"{dataset_key}_capstone_results_full.csv")
        capstone_metrics = binary_metrics(capstone_rows)
        protectai_rows = read_rows(input_dir / f"{dataset_key}_protectai_detector_results.csv")
        protectai_metrics = binary_metrics(protectai_rows, score_column="score")
        status = protectai_status(protectai_rows, runtime_notes_path)
        lines.append(
            f"| {display_name} | Capstone Hybrid Proxy | Local full evaluation | "
            f"{fmt(capstone_metrics.accuracy)} | {fmt(capstone_metrics.precision)} | "
            f"{fmt(capstone_metrics.recall)} | {fmt(capstone_metrics.f1)} | N/A |"
        )
        lines.append(
            f"| {display_name} | ProtectAI detector | {status} | "
            f"{fmt(protectai_metrics.accuracy)} | {fmt(protectai_metrics.precision)} | "
            f"{fmt(protectai_metrics.recall)} | {fmt(protectai_metrics.f1)} | "
            f"{fmt(protectai_metrics.auroc)} |"
        )

    lines.extend(
        [
            "",
            "#### Pending Baselines",
            "",
            "| Method | Status | Note |",
            "|---|---|---|",
            "| PIGuard | Pending | Main paper baseline; local metrics have not been produced yet. |",
            "| Meta Prompt Guard 2 | Pending | Executable candidate; local metrics have not been produced yet. |",
            "| Attention Tracker | Related work only | Excluded from the main local comparison because it requires internal attention scores. |",
        ]
    )
    if runtime_notes_path.exists():
        lines.extend(
            [
                "",
                "#### Runtime Note",
                "",
                "The ProtectAI detector rows marked Blocked indicate a model download/runtime failure and must not be interpreted as detector performance.",
            ]
        )
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--runtime-notes", default=str(RUNTIME_NOTES))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    runtime_notes_path = Path(args.runtime_notes)

    comparison_path = output_dir / "text_guard_comparison_table.md"
    readme_path = output_dir / "readme_text_guard_summary.md"
    write_lines(comparison_path, comparison_table(input_dir, runtime_notes_path))
    write_lines(readme_path, readme_summary(input_dir, runtime_notes_path))
    print(f"comparison={comparison_path}")
    print(f"readme={readme_path}")


if __name__ == "__main__":
    main()
