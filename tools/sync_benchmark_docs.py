from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.evaluate import run_evaluation


START_MARKER = "<!-- BENCHMARK:START -->"
END_MARKER = "<!-- BENCHMARK:END -->"
TARGET_FILES = [
    Path("README.md"),
    Path("docs/evaluation_method.md"),
]


def _render_block(dataset_path: Path) -> str:
    metrics = run_evaluation(dataset_path)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    dataset_size = metrics["meta"]["dataset_size"]
    pii_count = sum(1 for row in dataset if row.get("task") == "pii")
    inj_count = sum(1 for row in dataset if row.get("task") == "injection")

    pii = metrics["pii"]
    inj = metrics["injection"]

    return "\n".join(
        [
            START_MARKER,
            f"> `{dataset_path.as_posix()}` (총 {dataset_size}건) 기준 결과  ",
            f"> 생성 시각: {datetime.now().isoformat(timespec='seconds')}  ",
            "> 상세 결과: `reports/evaluation_report.md`",
            "",
            "| 항목 | Precision | Recall | F1 | TP / FP / FN |",
            "|---|---:|---:|---:|---:|",
            (
                f"| PII Detection | {pii['precision']:.3f} | {pii['recall']:.3f} | "
                f"{pii['f1']:.3f} | {pii['tp']} / {pii['fp']} / {pii['fn']} |"
            ),
            (
                f"| Prompt Injection Detection | {inj['precision']:.3f} | {inj['recall']:.3f} | "
                f"{inj['f1']:.3f} | {inj['tp']} / {inj['fp']} / {inj['fn']} |"
            ),
            END_MARKER,
        ]
    )


def _replace_block(content: str, block: str) -> str:
    start = content.find(START_MARKER)
    end = content.find(END_MARKER)
    if start == -1 or end == -1 or end < start:
        raise ValueError("Benchmark markers not found or invalid order.")
    end += len(END_MARKER)
    return content[:start] + block + content[end:]


def sync_docs(dataset_path: Path) -> None:
    block = _render_block(dataset_path)
    for path in TARGET_FILES:
        text = path.read_text(encoding="utf-8")
        updated = _replace_block(text, block)
        path.write_text(updated, encoding="utf-8")
        print(f"Updated benchmark block: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync benchmark table into markdown docs.")
    parser.add_argument(
        "--dataset",
        default="evaluation/sample_dataset.json",
        help="Path to evaluation dataset JSON.",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    sync_docs(dataset_path)


if __name__ == "__main__":
    main()
