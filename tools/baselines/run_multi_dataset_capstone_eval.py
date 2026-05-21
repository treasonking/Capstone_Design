"""Run Capstone Hybrid Proxy evaluation for full and matched multi-dataset subsets."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_capstone_detector_eval import evaluate_one_text, is_injection_result  # noqa: E402


DATASET_KEYS = ["deepset", "protectai", "lakera"]
DEFAULT_INPUT_DIR = Path("reports/baselines/multi_dataset")
FIELDNAMES = ["id", "label", "prediction", "action", "reason_codes"]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_success_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {row["id"] for row in csv.DictReader(f)}


def write_results(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for index, row in enumerate(rows, start=1):
            action, reason_codes = evaluate_one_text(row["text"])
            prediction = is_injection_result(action, reason_codes)
            writer.writerow(
                {
                    "id": row["id"],
                    "label": int(row["label"]),
                    "prediction": prediction,
                    "action": action,
                    "reason_codes": "|".join(reason_codes),
                }
            )
            print(
                f"[OK] {index}/{len(rows)} id={row['id']} "
                f"label={row['label']} action={action} pred={prediction}"
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument(
        "--detection-mode",
        choices=["hybrid", "regex_only", "model_only"],
        default="hybrid",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ["DETECTION_MODE"] = args.detection_mode
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for dataset_key in DATASET_KEYS:
        rows = read_rows(input_dir / f"{dataset_key}_shared_eval.csv")
        attention_ids = read_success_ids(output_dir / f"{dataset_key}_attention_tracker_results.csv")
        matched_rows = [row for row in rows if row["id"] in attention_ids]

        full_output = output_dir / f"{dataset_key}_capstone_results_full.csv"
        matched_output = output_dir / f"{dataset_key}_capstone_results_matched.csv"
        write_results(full_output, rows)
        write_results(matched_output, matched_rows)
        print(
            f"{dataset_key}: full_rows={len(rows)} matched_rows={len(matched_rows)} "
            f"full={full_output} matched={matched_output}"
        )


if __name__ == "__main__":
    main()
