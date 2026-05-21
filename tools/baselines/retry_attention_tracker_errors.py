"""Retry failed Attention Tracker rows from the shared baseline dataset."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_attention_tracker_eval import (
    evaluate_direct,
    read_dataset,
    resolve_repo_dir,
    write_error_header,
    append_error,
)


def read_error_ids(path: Path) -> set[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {row["id"] for row in csv.DictReader(f) if row.get("id")}


def write_setup_failures(
    rows: list[dict[str, str]],
    error_csv: Path,
    error: Exception,
) -> None:
    write_error_header(error_csv)
    for row in rows:
        text = (row.get("text") or row.get("data") or "").strip()
        append_error(
            error_csv,
            {
                "id": row.get("id", ""),
                "label": row.get("label", ""),
                "error": f"Attention Tracker retry setup failed: {error}",
                "query_preview": text[:500],
                "stdout_tail": "",
            },
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-csv", required=True)
    parser.add_argument("--error-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--retry-error-csv", required=True)
    parser.add_argument("--repo-dir", default=None)
    parser.add_argument("--model", default="qwen2-attn")
    parser.add_argument("--threshold", type=float, default=0.12)
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_rows = read_dataset(Path(args.dataset_csv))
    failed_ids = read_error_ids(Path(args.error_csv))
    retry_rows = [row for row in dataset_rows if row["id"] in failed_ids]

    if not retry_rows:
        raise ValueError(f"No retry rows found from {args.error_csv}")

    try:
        repo_dir = resolve_repo_dir(Path(args.repo_dir) if args.repo_dir else None)
        evaluate_direct(
            repo_dir=repo_dir,
            input_rows=retry_rows,
            output_csv=Path(args.output_csv),
            error_csv=Path(args.retry_error_csv),
            model_name=args.model,
            threshold=args.threshold,
        )
    except Exception as exc:
        Path(args.output_csv).parent.mkdir(parents=True, exist_ok=True)
        with Path(args.output_csv).open("w", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=["id", "label", "score", "prediction"]).writeheader()
        write_setup_failures(retry_rows, Path(args.retry_error_csv), exc)
        print(f"[DONE] retry setup failed for all rows: {exc}")
        print(f"[INFO] retry_rows={len(retry_rows)}")
        print(f"[INFO] results={args.output_csv}")
        print(f"[INFO] errors={args.retry_error_csv}")


if __name__ == "__main__":
    main()
