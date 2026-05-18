from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.external_datasets import (  # noqa: E402
    PROTECTAI_DATASET_NAME,
    PROTECTAI_FALLBACK_DATASET_NAME,
    _first_existing_key,
    _normalize_label,
    _rows_from_dataset,
)


REPORT_PATH = Path("reports/external_label_sanity_check.md")
RESULTS_JSON_PATH = Path("reports/external_label_sanity_check_results.json")
DATASETS = (
    ("deepset/prompt-injections", None),
    (PROTECTAI_DATASET_NAME, PROTECTAI_FALLBACK_DATASET_NAME),
)


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")[:180]


def _collect_samples(dataset_name: str, fallback: str | None, limit: int) -> list[dict[str, Any]]:
    rows = _rows_from_dataset(dataset_name, "all", fallback)
    grouped: dict[bool, list[dict[str, Any]]] = {True: [], False: []}

    for split_name, idx, row in rows:
        text_key = _first_existing_key(row, ["text", "prompt", "query", "instruction"])
        label_key = _first_existing_key(row, ["label", "labels", "is_injection", "injection"])
        if text_key is None or label_key is None:
            raise KeyError(f"Unsupported {dataset_name} row schema: {row.keys()}")

        expected = _normalize_label(row[label_key])
        if len(grouped[expected]) >= limit:
            continue
        grouped[expected].append(
            {
                "dataset_name": dataset_name,
                "split": split_name,
                "index": idx,
                "raw_label": row[label_key],
                "expected_injection": expected,
                "text": str(row[text_key]),
            }
        )
        if all(len(items) >= limit for items in grouped.values()):
            break

    return [*grouped[True], *grouped[False]]


def _render_report(generated_at: str, rows: list[dict[str, Any]]) -> str:
    lines = [
        "# External Label Sanity Check",
        "",
        f"- Generated at: `{generated_at}`",
        "",
        "## Sample Mapping",
        "",
        "| Dataset | Split | Index | Raw Label | expected_injection | Text Sample |",
        "|---|---|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['dataset_name']}` "
            f"| {row['split']} "
            f"| {row['index']} "
            f"| `{row['raw_label']}` "
            f"| {str(row['expected_injection']).lower()} "
            f"| {_escape(row['text'])} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `deepset/prompt-injections` label `1` is interpreted as injection and label `0` as safe/benign.",
            "- `protectai/prompt-injection-validation` positive labels are interpreted as injection and negative labels as safe/benign.",
            "- If these examples show the opposite semantic meaning, the external benchmark results must be considered invalid until label mapping is fixed.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(generated_at: str, rows: list[dict[str, Any]], path: Path) -> None:
    payload = {
        "generated_at": generated_at,
        "rows": rows,
        "interpretation": {
            "deepset": "label 1 -> injection, label 0 -> safe",
            "protectai": "positive labels -> injection, negative labels -> safe",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write sample label mappings for external prompt injection datasets.")
    parser.add_argument("--samples-per-class", type=int, default=5, help="Samples per positive/negative class.")
    parser.add_argument("--report", default=str(REPORT_PATH), help="Markdown report output path.")
    parser.add_argument("--json", default=str(RESULTS_JSON_PATH), help="JSON result output path.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    rows: list[dict[str, Any]] = []
    for dataset_name, fallback in DATASETS:
        rows.extend(_collect_samples(dataset_name, fallback, args.samples_per_class))

    generated_at = datetime.now().isoformat(timespec="seconds")
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(generated_at, rows), encoding="utf-8")
    _write_json(generated_at, rows, Path(args.json))
    print(f"External label sanity check report saved to: {args.report}")
    print(f"External label sanity check JSON saved to: {args.json}")


if __name__ == "__main__":
    main()
