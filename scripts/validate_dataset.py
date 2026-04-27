from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.dataset_common import VALID_LABELS, VALID_TASKS, counter_to_dict, labels_for_task, load_dataset


def _sample_id(row: dict[str, Any], index: int) -> str:
    return str(row.get("id", f"<missing:{index}>"))


def validate_dataset(path: str | Path) -> dict[str, Any]:
    rows = load_dataset(path)
    errors: list[str] = []
    warnings: list[str] = []
    ids: Counter[str] = Counter()
    texts: Counter[str] = Counter()
    task_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    positive = negative = 0

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"row[{index}] is not an object")
            continue

        sample_id = _sample_id(row, index)
        for field in ("id", "task", "text", "labels"):
            if field not in row:
                errors.append(f"{sample_id}: missing required field '{field}'")

        ids[sample_id] += 1
        text = row.get("text")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{sample_id}: text must be a non-empty string")
        else:
            texts[text] += 1

        task = row.get("task")
        if task not in VALID_TASKS:
            errors.append(f"{sample_id}: invalid task '{task}'")
        else:
            task_counts[str(task)] += 1

        labels = row.get("labels")
        if not isinstance(labels, list):
            errors.append(f"{sample_id}: labels must be a list")
            labels = []

        string_labels = [label for label in labels if isinstance(label, str)]
        if len(string_labels) != len(labels):
            errors.append(f"{sample_id}: every label must be a string")

        duplicate_labels = [label for label, count in Counter(string_labels).items() if count > 1]
        if duplicate_labels:
            errors.append(f"{sample_id}: duplicate labels {duplicate_labels}")

        unknown_labels = sorted(set(string_labels) - VALID_LABELS)
        if unknown_labels:
            errors.append(f"{sample_id}: undefined labels {unknown_labels}")

        if task in VALID_TASKS:
            wrong_task_labels = sorted(set(string_labels) - labels_for_task(str(task)))
            if wrong_task_labels:
                errors.append(f"{sample_id}: labels do not match task {wrong_task_labels}")

        if string_labels:
            positive += 1
            label_counts.update(string_labels)
        else:
            negative += 1

        category = str(row.get("category", ""))
        if sample_id.startswith("safe") and string_labels:
            warnings.append(f"{sample_id}: safe-prefixed sample has labels")
        if "boundary" in category and string_labels:
            warnings.append(f"{sample_id}: boundary category has positive labels")
        if task == "pii" and category.startswith("inj"):
            warnings.append(f"{sample_id}: pii task with injection-looking category")
        if task == "injection" and category.startswith("pii"):
            warnings.append(f"{sample_id}: injection task with pii-looking category")

    duplicate_ids = sorted(sample_id for sample_id, count in ids.items() if count > 1)
    duplicate_texts = sorted(text for text, count in texts.items() if count > 1)
    for sample_id in duplicate_ids:
        errors.append(f"duplicate id: {sample_id}")
    for text in duplicate_texts:
        warnings.append(f"duplicate text: {text[:80]}")

    return {
        "ok": not errors,
        "dataset_size": len(rows),
        "errors": errors,
        "warnings": warnings,
        "task_counts": counter_to_dict(task_counts),
        "label_counts": counter_to_dict(label_counts),
        "positive_count": positive,
        "negative_count": negative,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate detection dataset quality.")
    parser.add_argument("--dataset", default="datasets/sample_dataset_v2.json")
    args = parser.parse_args()

    result = validate_dataset(args.dataset)
    print(f"Dataset: {args.dataset}")
    print(f"Samples: {result['dataset_size']}")
    print(f"Positive / Negative: {result['positive_count']} / {result['negative_count']}")
    print(f"Task counts: {result['task_counts']}")
    print(f"Label counts: {result['label_counts']}")

    if result["warnings"]:
        print("\nWarnings:")
        for warning in result["warnings"]:
            print(f"- {warning}")
    if result["errors"]:
        print("\nErrors:")
        for error in result["errors"]:
            print(f"- {error}")
        raise SystemExit(1)
    print("\nValidation passed.")


if __name__ == "__main__":
    main()
