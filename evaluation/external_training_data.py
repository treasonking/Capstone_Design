from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.external_datasets import (  # noqa: E402
    ExternalSample,
    load_deepset_prompt_injections,
    load_lakera_gandalf_ignore_instructions,
    load_protectai_prompt_injection_validation,
)


DEFAULT_OUTPUT_DIR = Path("datasets/external_splits")
TRAIN_FILENAME = "train_external_prompt_injection.jsonl"
EVAL_FILENAME = "eval_external_prompt_injection.jsonl"
SUMMARY_FILENAME = "split_summary.json"
DEFAULT_RANDOM_SEED = 42
DEFAULT_TRAIN_RATIO = 0.7


DATASET_LOADERS = {
    "deepset/prompt-injections": load_deepset_prompt_injections,
    "protectai/prompt-injection-validation": load_protectai_prompt_injection_validation,
    "Lakera/gandalf_ignore_instructions": load_lakera_gandalf_ignore_instructions,
}


def _record_from_sample(sample: ExternalSample, index: int) -> dict[str, Any]:
    return {
        "id": f"{sample.source}:{sample.id or index}",
        "dataset": sample.source,
        "text": sample.text,
        "label": "injection" if sample.expected_injection else "safe",
    }


def _split_records(
    records: list[dict[str, Any]],
    *,
    train_ratio: float,
    random_seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[(str(record["dataset"]), str(record["label"]))].append(record)

    rng = random.Random(random_seed)
    train: list[dict[str, Any]] = []
    eval_rows: list[dict[str, Any]] = []
    clamped_ratio = max(0.0, min(train_ratio, 1.0))

    for _group_key, label_records in sorted(grouped.items()):
        shuffled = list(label_records)
        rng.shuffle(shuffled)
        if len(shuffled) <= 1:
            train.extend(shuffled)
            continue
        split_index = int(round(len(shuffled) * clamped_ratio))
        split_index = max(1, min(split_index, len(shuffled) - 1))
        train.extend(shuffled[:split_index])
        eval_rows.extend(shuffled[split_index:])

    train.sort(key=lambda item: str(item["id"]))
    eval_rows.sort(key=lambda item: str(item["id"]))
    return train, eval_rows


def _load_records(max_samples_per_dataset: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for dataset_name, loader in DATASET_LOADERS.items():
        samples = loader("all")
        if max_samples_per_dataset >= 0:
            samples = samples[:max_samples_per_dataset]
        for index, sample in enumerate(samples):
            records.append(_record_from_sample(sample, index))
    return records


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _counts(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        counts[str(row["dataset"])][str(row["label"])] += 1
    return {
        dataset: dict(sorted(counter.items()))
        for dataset, counter in sorted(counts.items())
    }


def _assert_no_overlap(train_rows: list[dict[str, Any]], eval_rows: list[dict[str, Any]]) -> int:
    train_ids = {str(row["id"]) for row in train_rows}
    eval_ids = {str(row["id"]) for row in eval_rows}
    overlap = train_ids & eval_ids
    if overlap:
        preview = ", ".join(sorted(overlap)[:5])
        raise SystemExit(f"Data leakage detected: train/eval split overlap found. {preview}")
    return 0


def _write_summary(
    *,
    path: Path,
    train_path: Path,
    eval_path: Path,
    train_rows: list[dict[str, Any]],
    eval_rows: list[dict[str, Any]],
    random_seed: int,
    train_ratio: float,
) -> None:
    overlap_count = _assert_no_overlap(train_rows, eval_rows)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "random_seed": random_seed,
        "train_ratio": train_ratio,
        "eval_ratio": round(1.0 - train_ratio, 6),
        "train_path": str(train_path),
        "eval_path": str(eval_path),
        "train_size": len(train_rows),
        "eval_size": len(eval_rows),
        "train_counts": _counts(train_rows),
        "eval_counts": _counts(eval_rows),
        "train_eval_overlap": overlap_count,
        "leakage_check": "passed",
        "note": (
            "Lakera/gandalf_ignore_instructions is attack-focused; precision/F1 for that dataset "
            "should be interpreted only when safe negatives are present."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create deterministic train/eval splits for external prompt injection datasets."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for split files.")
    parser.add_argument("--train-ratio", type=float, default=DEFAULT_TRAIN_RATIO, help="Train split ratio.")
    parser.add_argument("--random-seed", type=int, default=DEFAULT_RANDOM_SEED, help="Deterministic random seed.")
    parser.add_argument(
        "--max-samples-per-dataset",
        type=int,
        default=-1,
        help="Optional cap per dataset before splitting. -1 means full dataset.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    output_dir = Path(args.output_dir)
    train_path = output_dir / TRAIN_FILENAME
    eval_path = output_dir / EVAL_FILENAME
    summary_path = output_dir / SUMMARY_FILENAME

    records = _load_records(args.max_samples_per_dataset)
    train_rows, eval_rows = _split_records(
        records,
        train_ratio=args.train_ratio,
        random_seed=args.random_seed,
    )
    _assert_no_overlap(train_rows, eval_rows)
    _write_jsonl(train_path, train_rows)
    _write_jsonl(eval_path, eval_rows)
    _write_summary(
        path=summary_path,
        train_path=train_path,
        eval_path=eval_path,
        train_rows=train_rows,
        eval_rows=eval_rows,
        random_seed=args.random_seed,
        train_ratio=args.train_ratio,
    )
    print(f"External train split saved to: {train_path}")
    print(f"External eval split saved to: {eval_path}")
    print(f"External split summary saved to: {summary_path}")


if __name__ == "__main__":
    main()
