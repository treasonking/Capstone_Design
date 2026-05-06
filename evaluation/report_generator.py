from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def _dataset_notice(dataset_path: str) -> list[str]:
    dataset_name = Path(dataset_path).name.lower()
    if dataset_name == "sample_dataset.json":
        return [
            "> 이 리포트는 내부 회귀 테스트 데이터셋 기준 결과이다. 탐지 룰과 정책이 기존 테스트 케이스에서 정상 동작하는지 확인하기 위한 목적이며, 실제 운영 환경의 일반화 성능을 의미하지 않는다.",
            "",
        ]
    if dataset_name == "external_validation_sample.json":
        return [
            "> 이 리포트는 내부 데이터셋 과적합 가능성을 보완하기 위한 외부 스타일 검증 결과이다. 외부 표현, 우회 문장, 다양한 프롬프트 스타일에서 탐지 성능이 어떻게 달라지는지 확인하기 위한 목적이다.",
            "",
        ]
    return []


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


def _metric_row(name: str, metric: dict[str, Any]) -> str:
    return (
        f"| {name} | {metric['precision']:.3f} | {metric['recall']:.3f} | "
        f"{metric['f1']:.3f} | {metric['tp']} | {metric['fp']} | {metric['fn']} |"
    )


def _render_reason_code_metrics(metrics: dict[str, Any]) -> list[str]:
    lines = [
        "## Reason Code Metrics",
        "",
        "| reason_code | precision | recall | f1 | TP | FP | FN |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for reason_code, metric in metrics["reason_code_metrics"].items():
        lines.append(_metric_row(reason_code, metric))
    lines.append("")
    return lines


def _render_focused_risk_areas(metrics: dict[str, Any]) -> list[str]:
    lines = ["## Focused Risk Areas", ""]
    for reason_code, metric in metrics["focused_risk_areas"].items():
        lines.extend(
            [
                f"### {reason_code}",
                "",
                f"- Precision: **{metric['precision']:.3f}**",
                f"- Recall: **{metric['recall']:.3f}**",
                f"- F1: **{metric['f1']:.3f}**",
                f"- TP / FP / FN: **{metric['tp']} / {metric['fp']} / {metric['fn']}**",
                "",
            ]
        )
    return lines


def _render_error_table(title: str, sections: list[dict[str, Any]], key: str) -> list[str]:
    rows: list[dict[str, Any]] = []
    for section in sections:
        rows.extend(section.get(key, []))

    lines = [
        f"## {title}",
        "",
        "| id | expected | actual | text_excerpt | suspected_cause |",
        "|---|---|---|---|---|",
    ]
    if not rows:
        lines.append("| - | - | - | - | - |")
    for row in rows:
        excerpt = str(row["text_excerpt"]).replace("|", "\\|")
        lines.append(
            f"| {row['id']} | `{row['expected']}` | `{row['actual']}` | {excerpt} | {row['suspected_cause']} |"
        )
    lines.append("")
    return lines


def _render_hybrid_cases(metrics: dict[str, Any]) -> list[str]:
    hybrid = metrics.get("hybrid", {})
    if not hybrid:
        return []

    lines = [
        "## Hybrid Attack Detection",
        "",
        f"- Passed: **{hybrid.get('passed', 0)} / {hybrid.get('total', 0)}**",
        f"- Failed: **{hybrid.get('failed', 0)}**",
        "",
        "| Case | Text | Expected | Actual | Result |",
        "|---|---|---|---|---|",
    ]
    for row in hybrid.get("cases", []):
        text = str(row.get("text", "")).replace("|", "\\|")
        lines.append(
            f"| {row.get('id', '')} | {text} | {row.get('expected_action', '')} | {row.get('actual_action', '')} | {row.get('result', '')} |"
        )
    if not hybrid.get("cases"):
        lines.append("| - | - | - | - | - |")
    lines.append("")
    return lines


def generate_markdown_report(metrics: dict[str, Any], output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Detection Evaluation Report",
        "",
    ]
    lines.extend(_dataset_notice(str(metrics["meta"].get("dataset", ""))))
    lines.extend(
        [
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        f"- Dataset: `{metrics['meta'].get('dataset', '')}`",
        f"- Dataset size: {metrics['meta']['dataset_size']}",
        "",
        "## Summary",
        "",
        "| task | precision | recall | f1 | TP | FP | FN |",
        "|---|---:|---:|---:|---:|---:|---:|",
        _metric_row("pii", metrics["pii"]),
        _metric_row("injection", metrics["injection"]),
        "",
        ]
    )
    lines.extend(_render_metric_block("PII Detection", metrics["pii"]))
    lines.extend(_render_metric_block("Prompt Injection Detection", metrics["injection"]))
    lines.extend(_render_hybrid_cases(metrics))
    lines.extend(_render_reason_code_metrics(metrics))
    lines.extend(_render_focused_risk_areas(metrics))
    lines.extend(_render_error_table("False Positives", [metrics["pii"], metrics["injection"]], "false_positives"))
    lines.extend(_render_error_table("False Negatives", [metrics["pii"], metrics["injection"]], "false_negatives"))
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
