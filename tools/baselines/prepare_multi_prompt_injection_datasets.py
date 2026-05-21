"""Prepare deepset, ProtectAI, and Lakera prompt-injection baseline CSVs."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DATASETS = {
    "deepset": "deepset/prompt-injections",
    "protectai": "protectai/prompt-injection-validation",
    "lakera": "Lakera/gandalf_ignore_instructions",
}
DEFAULT_OUTPUT_DIR = Path("reports/baselines/multi_dataset")
DEFAULT_INSTRUCTION = "Say xxxxxx"
DEFAULT_LIMIT = 100


@dataclass(frozen=True, slots=True)
class Sample:
    source_id: str
    dataset: str
    text: str
    label: int


def normalize_label(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        if value in {0, 1}:
            return value
    text = str(value).strip().lower()
    if text in {"1", "true", "attack", "malicious", "injection", "jailbreak", "unsafe"}:
        return 1
    if text in {"0", "false", "benign", "normal", "safe", "legit", "not_injection"}:
        return 0
    raise ValueError(f"Unsupported label value: {value!r}")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def sample_from_row(row: dict[str, Any], dataset_name: str) -> Sample:
    return Sample(
        source_id=str(row.get("id", "")),
        dataset=dataset_name,
        text=str(row["text"]),
        label=normalize_label(row["label"]),
    )


def load_current_deepset_subset() -> list[Sample]:
    path = Path("data/external/attention_tracker/shared_prompt_injection_eval.csv")
    if not path.exists():
        return []
    return [
        Sample(
            source_id=str(row["id"]),
            dataset=DATASETS["deepset"],
            text=row["text"],
            label=normalize_label(row["label"]),
        )
        for row in read_csv_rows(path)
    ]


def load_internal_external_split(dataset_name: str) -> list[Sample]:
    paths = [
        Path("datasets/external_splits/eval_external_prompt_injection.jsonl"),
        Path("datasets/external_splits/train_external_prompt_injection.jsonl"),
    ]
    samples: list[Sample] = []
    seen_ids: set[str] = set()
    for path in paths:
        if not path.exists():
            continue
        for row in read_jsonl_rows(path):
            if row.get("dataset") != dataset_name:
                continue
            source_id = str(row.get("id", ""))
            if source_id in seen_ids:
                continue
            seen_ids.add(source_id)
            samples.append(sample_from_row(row, dataset_name))
    return samples


def select_balanced(samples: list[Sample], limit: int) -> tuple[list[Sample], str]:
    attacks = [sample for sample in samples if sample.label == 1]
    benign = [sample for sample in samples if sample.label == 0]
    if attacks and benign:
        per_class = min(limit // 2, len(attacks), len(benign))
        selected: list[Sample] = []
        for attack, safe in zip(attacks[:per_class], benign[:per_class]):
            selected.extend([attack, safe])
        remaining = limit - len(selected)
        if remaining > 0:
            selected.extend(attacks[per_class : per_class + remaining])
        return selected[:limit], f"balanced attack={per_class}, benign={per_class}"

    selected = samples[:limit]
    reason = "single-class source; balanced 50/50 subset unavailable"
    return selected, reason


def write_dataset_csv(
    output_path: Path,
    dataset_key: str,
    samples: list[Sample],
    instruction: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "dataset", "text", "label", "instruction"],
        )
        writer.writeheader()
        for index, sample in enumerate(samples, start=1):
            writer.writerow(
                {
                    "id": f"{dataset_key}-{index:03d}",
                    "dataset": sample.dataset,
                    "text": sample.text,
                    "label": sample.label,
                    "instruction": instruction,
                }
            )


def write_source_notes(
    output_dir: Path,
    notes: list[dict[str, str | int]],
) -> None:
    lines = [
        "# Multi-Dataset Source Notes",
        "",
        "No HuggingFace download was required for this run; all selected rows came from repository-local files.",
        "",
        "| Dataset | Source | Split | Original columns | Label mapping | Selected sample count | Note |",
        "|---|---|---|---|---|---:|---|",
    ]
    for note in notes:
        lines.append(
            "| {dataset} | {source} | {split} | {columns} | {mapping} | {count} | {note} |".format(
                **note
            )
        )
    (output_dir / "dataset_source_notes.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--instruction", default=DEFAULT_INSTRUCTION)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    notes: list[dict[str, str | int]] = []
    for dataset_key, dataset_name in DATASETS.items():
        if dataset_key == "deepset":
            samples = load_current_deepset_subset()
            source = "data/external/attention_tracker/shared_prompt_injection_eval.csv"
            split = "capstone-selected subset"
            columns = "id,text,label,instruction"
            selection_note = "preserves previous Attention Tracker local reproduction subset"
        else:
            samples = load_internal_external_split(dataset_name)
            source = "datasets/external_splits/eval_external_prompt_injection.jsonl; datasets/external_splits/train_external_prompt_injection.jsonl"
            split = "repo-local external_splits"
            columns = "id,dataset,text,label"
            samples, selection_note = select_balanced(samples, args.limit)

        if dataset_key == "deepset":
            samples = samples[: args.limit]
        if not samples:
            raise RuntimeError(f"No samples found for {dataset_name}")

        output_path = output_dir / f"{dataset_key}_shared_eval.csv"
        write_dataset_csv(output_path, dataset_key, samples, args.instruction)
        notes.append(
            {
                "dataset": dataset_key,
                "source": source,
                "split": split,
                "columns": columns,
                "mapping": "injection/attack/jailbreak/unsafe=1; safe/benign/normal=0",
                "count": len(samples),
                "note": selection_note,
            }
        )

        attacks = sum(1 for sample in samples if sample.label == 1)
        benign = sum(1 for sample in samples if sample.label == 0)
        print(f"{dataset_key}: rows={len(samples)} attack={attacks} benign={benign} output={output_path}")

    write_source_notes(output_dir, notes)
    print(f"source_notes={output_dir / 'dataset_source_notes.md'}")


if __name__ == "__main__":
    main()
