"""Merge base and retry Attention Tracker result CSV files."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


FIELDNAMES = ["id", "label", "score", "prediction"]


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-csv", required=True)
    parser.add_argument("--base-csv", required=True)
    parser.add_argument("--retry-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--missing-csv", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_rows = read_rows(Path(args.dataset_csv))
    base_rows = read_rows(Path(args.base_csv))
    retry_rows = read_rows(Path(args.retry_csv))

    merged_by_id: dict[str, dict[str, str]] = {}
    for row in base_rows:
        merged_by_id[row["id"]] = {field: row.get(field, "") for field in FIELDNAMES}
    for row in retry_rows:
        merged_by_id[row["id"]] = {field: row.get(field, "") for field in FIELDNAMES}

    dataset_ids = [row["id"] for row in dataset_rows]
    merged_rows = [merged_by_id[sample_id] for sample_id in dataset_ids if sample_id in merged_by_id]
    missing_rows = [
        {
            "id": row["id"],
            "label": row["label"],
            "text": row.get("text") or row.get("data") or "",
        }
        for row in dataset_rows
        if row["id"] not in merged_by_id
    ]

    write_rows(Path(args.output_csv), merged_rows, FIELDNAMES)
    write_rows(Path(args.missing_csv), missing_rows, ["id", "label", "text"])

    print(f"dataset_rows={len(dataset_rows)}")
    print(f"success_rows={len(merged_rows)}")
    print(f"missing_rows={len(missing_rows)}")
    print(f"output={args.output_csv}")
    print(f"missing={args.missing_csv}")


if __name__ == "__main__":
    main()
