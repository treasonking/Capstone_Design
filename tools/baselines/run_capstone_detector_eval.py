"""Evaluate the capstone hybrid detector on the shared baseline dataset."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path


INJECTION_REASON_KEYWORDS = [
    "INJ_",
    "PROMPT_INJECTION",
    "JAILBREAK",
    "POLICY_BYPASS",
    "DIRECT_OVERRIDE",
    "SYSTEM_PROMPT",
    "IGNORE_INSTRUCTION",
    "MODEL_INJECTION_RISK",
]
PII_REASON_PREFIXES = ("PII_", "MODEL_PII")


def is_injection_result(action: str, reason_codes: list[str]) -> int:
    joined = " ".join(reason_codes).upper()
    if any(keyword in joined for keyword in INJECTION_REASON_KEYWORDS):
        return 1
    if any(code.upper().startswith(PII_REASON_PREFIXES) for code in reason_codes):
        return 0
    if action.upper() in {"BLOCK", "WARN"} and "SAFE_INPUT" not in joined:
        return 1
    return 0


def evaluate_one_text(text: str) -> tuple[str, list[str]]:
    repo_root = Path.cwd().resolve()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from backend.app.detection.hybrid_detector import detect_hybrid

    result = detect_hybrid(text)
    reason_codes = list(result.reason_codes) if result.reason_codes else ["SAFE_INPUT"]
    return result.action, reason_codes


def read_match_ids(path: Path | None) -> set[str] | None:
    if path is None:
        return None
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {row["id"] for row in csv.DictReader(f)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--match-results-csv",
        default=None,
        help="Optional result CSV whose ids define the exact subset to evaluate.",
    )
    parser.add_argument(
        "--detection-mode",
        choices=["hybrid", "regex_only", "model_only"],
        default="hybrid",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    os.environ["DETECTION_MODE"] = args.detection_mode

    input_path = Path(args.input_csv)
    output_path = Path(args.output_csv)
    match_ids = read_match_ids(Path(args.match_results_csv) if args.match_results_csv else None)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if args.limit is not None:
        rows = rows[: args.limit]
    if match_ids is not None:
        rows = [row for row in rows if row["id"] in match_ids]

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["id", "label", "prediction", "action", "reason_codes"],
        )
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

    print(f"[DONE] rows={len(rows)} output={output_path}")


if __name__ == "__main__":
    main()
