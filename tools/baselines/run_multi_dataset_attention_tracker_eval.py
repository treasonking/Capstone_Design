"""Run Attention Tracker baseline evaluation for multiple prompt-injection datasets."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_attention_tracker_eval import (  # noqa: E402
    append_error,
    evaluate_direct,
    import_precomputed,
    read_dataset,
    resolve_repo_dir,
    row_text,
    write_error_header,
    write_result_header,
)


DATASET_KEYS = ["deepset", "protectai", "lakera"]
DEFAULT_INPUT_DIR = Path("reports/baselines/multi_dataset")
DEFAULT_PRECOMPUTED_RESULTS = Path("reports/baselines/attention_tracker_results.csv")
DEFAULT_PRECOMPUTED_ERRORS = Path("reports/baselines/attention_tracker_errors.csv")


def write_setup_failures(
    rows: list[dict[str, str]],
    output_csv: Path,
    error_csv: Path,
    error: Exception,
) -> None:
    write_result_header(output_csv)
    write_error_header(error_csv)
    for row in rows:
        append_error(
            error_csv,
            {
                "id": row.get("id", ""),
                "label": row.get("label", ""),
                "error": f"Attention Tracker setup failed: {error}",
                "query_preview": row_text(row)[:500],
                "stdout_tail": "",
            },
        )


def remap_deepset_ids_for_precomputed(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    remapped: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=1):
        copied = dict(row)
        copied["id"] = str(index)
        remapped.append(copied)
    return remapped


def restore_deepset_ids(output_csv: Path, dataset_key: str) -> None:
    with output_csv.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "label", "score", "prediction"])
        writer.writeheader()
        for row in rows:
            row["id"] = f"{dataset_key}-{int(row['id']):03d}"
            writer.writerow(row)


def restore_deepset_error_ids(error_csv: Path, dataset_key: str) -> None:
    with error_csv.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    with error_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "label", "error", "query_preview", "stdout_tail"],
        )
        writer.writeheader()
        for row in rows:
            row["id"] = f"{dataset_key}-{int(row['id']):03d}"
            writer.writerow(row)


def run_one_dataset(
    *,
    dataset_key: str,
    input_csv: Path,
    output_csv: Path,
    error_csv: Path,
    model: str,
    threshold: float,
    repo_dir: Path | None,
    use_deepset_precomputed: bool,
) -> None:
    rows = read_dataset(input_csv)
    if dataset_key == "deepset" and use_deepset_precomputed and DEFAULT_PRECOMPUTED_RESULTS.exists():
        import_precomputed(
            input_rows=remap_deepset_ids_for_precomputed(rows),
            output_csv=output_csv,
            error_csv=error_csv,
            precomputed_csv=DEFAULT_PRECOMPUTED_RESULTS,
            precomputed_error_csv=(
                DEFAULT_PRECOMPUTED_ERRORS
                if DEFAULT_PRECOMPUTED_ERRORS.exists()
                else None
            ),
            threshold=threshold,
        )
        restore_deepset_ids(output_csv, dataset_key)
        restore_deepset_error_ids(error_csv, dataset_key)
        return

    try:
        resolved_repo_dir = resolve_repo_dir(repo_dir)
        evaluate_direct(
            repo_dir=resolved_repo_dir,
            input_rows=rows,
            output_csv=output_csv,
            error_csv=error_csv,
            model_name=model,
            threshold=threshold,
        )
    except Exception as exc:
        write_setup_failures(rows, output_csv, error_csv, exc)
        print(f"[DONE] {dataset_key}: setup failed for all rows: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--repo-dir", default=None)
    parser.add_argument("--model", default="qwen2-attn")
    parser.add_argument("--threshold", type=float, default=0.12)
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    parser.add_argument(
        "--no-deepset-precomputed",
        action="store_true",
        help="Force direct Attention Tracker execution for deepset instead of reusing prior local reproduction rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    repo_dir = Path(args.repo_dir) if args.repo_dir else None

    for dataset_key in DATASET_KEYS:
        input_csv = input_dir / f"{dataset_key}_shared_eval.csv"
        output_csv = output_dir / f"{dataset_key}_attention_tracker_results.csv"
        error_csv = output_dir / f"{dataset_key}_attention_tracker_errors.csv"
        run_one_dataset(
            dataset_key=dataset_key,
            input_csv=input_csv,
            output_csv=output_csv,
            error_csv=error_csv,
            model=args.model,
            threshold=args.threshold,
            repo_dir=repo_dir,
            use_deepset_precomputed=not args.no_deepset_precomputed,
        )
        print(f"{dataset_key}: results={output_csv} errors={error_csv}")


if __name__ == "__main__":
    main()
