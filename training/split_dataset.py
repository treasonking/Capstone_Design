from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_PATH = PROJECT_ROOT / "datasets" / "security_proxy_dataset.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "datasets" / "processed"


def load_jsonl(path: str | Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def assign_splits(records: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("template_id", "default"))].append(dict(record))

    updated: list[dict[str, object]] = []
    for index, template_id in enumerate(sorted(grouped)):
        if index % 20 in {0, 1, 2}:
            split = "test"
        elif index % 20 in {3, 4, 5}:
            split = "valid"
        else:
            split = "train"
        for record in grouped[template_id]:
            record["split"] = split
            updated.append(record)
    return updated


def write_splits(records: list[dict[str, object]], output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> dict[str, Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    split_map = {"train": [], "valid": [], "test": []}
    for record in records:
        split_map[str(record["split"])].append(record)

    output_paths: dict[str, Path] = {}
    for split, items in split_map.items():
        output_path = directory / f"{split}.jsonl"
        with output_path.open("w", encoding="utf-8") as file:
            for item in items:
                file.write(json.dumps(item, ensure_ascii=False) + "\n")
        output_paths[split] = output_path
    return output_paths


def rewrite_dataset(records: list[dict[str, object]], dataset_path: str | Path = DEFAULT_DATASET_PATH) -> Path:
    output_path = Path(dataset_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Split the hybrid security dataset into train/valid/test JSONL files.")
    parser.add_argument("--input", default=str(DEFAULT_DATASET_PATH), help="Input JSONL dataset path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for split JSONL files.")
    args = parser.parse_args()

    records = load_jsonl(args.input)
    updated = assign_splits(records)
    rewrite_dataset(updated, args.input)
    outputs = write_splits(updated, args.output_dir)
    for split, path in outputs.items():
        print(f"{split}: {path}")


if __name__ == "__main__":
    main()
