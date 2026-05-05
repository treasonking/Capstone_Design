from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import re
from pathlib import Path

from training.prepare_dataset import DEFAULT_OUTPUT_PATH as DEFAULT_DATASET_PATH
from training.prepare_dataset import build_dataset, write_jsonl
from training.split_dataset import DEFAULT_OUTPUT_DIR, assign_splits, load_jsonl, rewrite_dataset, write_splits


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "reports" / "dataset_bias_check.md"


def _ensure_dataset() -> list[dict[str, object]]:
    if not DEFAULT_DATASET_PATH.exists():
        DEFAULT_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(build_dataset(), DEFAULT_DATASET_PATH)
    records = load_jsonl(DEFAULT_DATASET_PATH)
    split_paths = {split: DEFAULT_OUTPUT_DIR / f"{split}.jsonl" for split in ("train", "valid", "test")}
    if not all(path.exists() for path in split_paths.values()):
        assigned = assign_splits(records)
        rewrite_dataset(assigned, DEFAULT_DATASET_PATH)
        write_splits(assigned, DEFAULT_OUTPUT_DIR)
        records = assigned
    return records


def _template_signature(text: str) -> str:
    normalized = text.lower()
    normalized = re.sub(r"[0-9]", "#", normalized)
    normalized = re.sub(r"[가-힣]{2,4}(?=님|씨|주무관|과장)", "<name>", normalized)
    normalized = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,24}", "<email>", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def build_report(records: list[dict[str, object]]) -> str:
    total = len(records)
    split_counts = Counter(str(record.get("split", "unassigned")) for record in records)
    label_counts = Counter(str(record["label"]) for record in records)
    pii_counts = Counter()
    injection_counts = Counter()
    exact_duplicates = total - len({str(record["text"]) for record in records})
    signature_counter = Counter(_template_signature(str(record["text"])) for record in records)
    near_duplicates = sum(count - 1 for count in signature_counter.values() if count > 1)

    for record in records:
        for pii_type in record.get("pii_types", []):
            pii_counts[str(pii_type)] += 1
        for injection_type in record.get("injection_types", []):
            injection_type = str(injection_type)
            if injection_type != "none":
                injection_counts[injection_type] += 1

    split_signatures: dict[str, set[str]] = defaultdict(set)
    for record in records:
        split_signatures[str(record.get("split", "unassigned"))].add(_template_signature(str(record["text"])))
    leakage_pairs = {
        "train/test": len(split_signatures["train"] & split_signatures["test"]),
        "train/valid": len(split_signatures["train"] & split_signatures["valid"]),
        "valid/test": len(split_signatures["valid"] & split_signatures["test"]),
    }
    leakage_risk = "low" if all(value == 0 for value in leakage_pairs.values()) else "review-needed"

    lines = [
        "# Dataset Bias and Overfitting Check",
        "",
        "## 1. Dataset Size",
        f"- Total: {total}",
        f"- Train: {split_counts.get('train', 0)}",
        f"- Validation: {split_counts.get('valid', 0)}",
        f"- Test: {split_counts.get('test', 0)}",
        "",
        "## 2. Label Distribution",
        "| Label | Count | Ratio |",
        "|---|---:|---:|",
    ]
    for label, count in sorted(label_counts.items()):
        lines.append(f"| {label} | {count} | {count / total:.3f} |")

    lines.extend(["", "## 3. PII Type Distribution", "| PII Type | Count |", "|---|---:|"])
    for pii_type, count in sorted(pii_counts.items()):
        lines.append(f"| {pii_type} | {count} |")

    lines.extend(["", "## 4. Injection Type Distribution", "| Injection Type | Count |", "|---|---:|"])
    for injection_type, count in sorted(injection_counts.items()):
        lines.append(f"| {injection_type} | {count} |")

    lines.extend(
        [
            "",
            "## 5. Duplication Check",
            f"- Exact duplicates: {exact_duplicates}",
            f"- Near duplicates: {near_duplicates}",
            f"- Template leakage risk: {leakage_risk}",
            "",
            "## 6. Split Leakage Check",
            f"- Similar templates across train/test: {leakage_pairs['train/test']}",
            f"- Similar templates across train/valid: {leakage_pairs['train/valid']}",
            f"- Similar templates across valid/test: {leakage_pairs['valid/test']}",
            "",
            "## 7. Conclusion",
        ]
    )
    balanced = 0.25 <= (label_counts.get("safe", 0) / max(total, 1)) <= 0.45
    conclusion = "Dataset is balanced enough for baseline hybrid experiments." if balanced and leakage_risk == "low" else "Dataset needs improvement before high-confidence claims."
    lines.append(f"- {conclusion}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check dataset balance and leakage for the hybrid proxy dataset.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH), help="Dataset JSONL path.")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        write_jsonl(build_dataset(), dataset_path)
    records = _ensure_dataset()
    report = build_report(records)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(json.dumps({"report": str(REPORT_PATH), "total": len(records)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
