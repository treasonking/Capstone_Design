from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def _render_metric_block(name: str, metric: dict[str, Any]) -> list[str]:
    return [
        f"### {name}",
        "",
        f"- Precision: **{metric['precision']:.3f}**",
        f"- Recall: **{metric['recall']:.3f}**",
        f"- F1: **{metric['f1']:.3f}**",
        f"- TP / FP / FN: **{metric['tp']} / {metric['fp']} / {metric['fn']}**",
        f"- False Positives (sample count): **{len(metric['false_positive_ids'])}**",
        f"- False Negatives (sample count): **{len(metric['false_negative_ids'])}**",
        "",
    ]


def generate_markdown_report(metrics: dict[str, Any], output_path: str | Path) -> Path:
    output = Path(output_path)
    lines = [
        "# Detection Evaluation Report",
        "",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Dataset size: {metrics['meta']['dataset_size']}",
        "",
    ]
    lines.extend(_render_metric_block("PII Detection", metrics["pii"]))
    lines.extend(_render_metric_block("Prompt Injection Detection", metrics["injection"]))
    output.write_text("\n".join(lines), encoding="utf-8")
    return output

