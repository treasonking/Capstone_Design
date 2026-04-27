from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.dataset_common import counter_to_dict, load_dataset


def dataset_stats(path: str | Path) -> dict[str, Any]:
    rows = load_dataset(path)
    task_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    difficulty_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    positive = negative = multilabel = boundary = 0
    total_labels = 0

    for row in rows:
        labels = row.get("labels", [])
        task_counts.update([str(row.get("task", "<missing>"))])
        label_counts.update(labels)
        difficulty_counts.update([str(row.get("difficulty", "<missing>"))])
        category_counts.update([str(row.get("category", "<missing>"))])
        total_labels += len(labels)
        if labels:
            positive += 1
        else:
            negative += 1
        if len(labels) > 1:
            multilabel += 1
        if row.get("difficulty") == "hard" or "boundary" in str(row.get("category", "")) or "boundary" in str(row.get("notes", "")).lower():
            boundary += 1

    return {
        "dataset_size": len(rows),
        "task_counts": counter_to_dict(task_counts),
        "positive_count": positive,
        "negative_count": negative,
        "label_counts": counter_to_dict(label_counts),
        "multilabel_count": multilabel,
        "difficulty_counts": counter_to_dict(difficulty_counts),
        "category_counts": counter_to_dict(category_counts),
        "average_labels_per_sample": round(total_labels / len(rows), 3) if rows else 0.0,
        "boundary_candidate_count": boundary,
    }


def _markdown_table(title: str, values: dict[str, int]) -> list[str]:
    lines = [f"## {title}", "", "| Key | Count |", "|---|---:|"]
    lines.extend(f"| {key} | {value} |" for key, value in values.items())
    lines.append("")
    return lines


def write_markdown(stats: dict[str, Any], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Dataset Statistics",
        "",
        f"- Dataset size: **{stats['dataset_size']}**",
        f"- Positive / Negative: **{stats['positive_count']} / {stats['negative_count']}**",
        f"- Multilabel samples: **{stats['multilabel_count']}**",
        f"- Average labels per sample: **{stats['average_labels_per_sample']}**",
        f"- Boundary candidates: **{stats['boundary_candidate_count']}**",
        "",
    ]
    lines.extend(_markdown_table("Task Counts", stats["task_counts"]))
    lines.extend(_markdown_table("Difficulty Counts", stats["difficulty_counts"]))
    lines.extend(_markdown_table("Label Counts", stats["label_counts"]))
    lines.extend(_markdown_table("Category Counts", stats["category_counts"]))
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize detection dataset distribution.")
    parser.add_argument("--dataset", default="datasets/sample_dataset_v2.json")
    parser.add_argument("--json-output", default="reports/dataset_stats.json")
    parser.add_argument("--markdown-output", default="reports/dataset_stats.md")
    args = parser.parse_args()

    stats = dataset_stats(args.dataset)
    json_output = Path(args.json_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_output = write_markdown(stats, args.markdown_output)

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"JSON saved to: {json_output}")
    print(f"Markdown saved to: {md_output}")


if __name__ == "__main__":
    main()
