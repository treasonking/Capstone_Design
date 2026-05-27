"""Run Capstone Hybrid Proxy evaluation for the selected multi-dataset subsets."""

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
        full_output = output_dir / f"{dataset_key}_capstone_results_full.csv"
        write_results(full_output, rows)
        print(f"{dataset_key}: full_rows={len(rows)} full={full_output}")


if __name__ == "__main__":
    main()
