from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
from typing import Any

try:
    import pandas as pd  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    pd = None

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
except ModuleNotFoundError:  # pragma: no cover
    SimpleDocTemplate = None


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


def generate_markdown_report(metrics: dict[str, Any], output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Detection Evaluation Report",
        "",
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
    lines.extend(_render_metric_block("PII Detection", metrics["pii"]))
    lines.extend(_render_metric_block("Prompt Injection Detection", metrics["injection"]))
    lines.extend(_render_reason_code_metrics(metrics))
    lines.extend(_render_focused_risk_areas(metrics))
    lines.extend(_render_error_table("False Positives", [metrics["pii"], metrics["injection"]], "false_positives"))
    lines.extend(_render_error_table("False Negatives", [metrics["pii"], metrics["injection"]], "false_negatives"))
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _safe_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def load_locust_metrics(csv_path: str | Path) -> dict[str, float]:
    csv_file = Path(csv_path)
    if pd is not None:
        dataframe = pd.read_csv(csv_file)
        if {"metric", "value"}.issubset(dataframe.columns):
            metric_map = {
                str(row["metric"]).strip(): _safe_float(row["value"])
                for _, row in dataframe.iterrows()
            }
            return {
                "total_requests": metric_map.get("total_requests", 0.0),
                "failures": metric_map.get("failures", 0.0),
                "error_rate": metric_map.get("error_rate", 0.0),
                "average_latency_ms": metric_map.get("average_latency_ms", 0.0),
                "p95_latency_ms": metric_map.get("p95_latency_ms", 0.0),
                "requests_per_sec": metric_map.get("requests_per_sec", 0.0),
            }
        if {"Type", "Name", "Request Count", "Failure Count", "Average Response Time", "95%", "Requests/s"}.issubset(dataframe.columns):
            aggregate = dataframe.iloc[0]
            request_count = _safe_float(aggregate["Request Count"])
            failure_count = _safe_float(aggregate["Failure Count"])
            error_rate = 0.0 if request_count == 0 else (failure_count / request_count) * 100
            return {
                "total_requests": request_count,
                "failures": failure_count,
                "error_rate": error_rate,
                "average_latency_ms": _safe_float(aggregate["Average Response Time"]),
                "p95_latency_ms": _safe_float(aggregate["95%"]),
                "requests_per_sec": _safe_float(aggregate["Requests/s"]),
            }

    with csv_file.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
    if rows and {"metric", "value"}.issubset(rows[0].keys()):
        metric_map = {
            str(row["metric"]).strip(): _safe_float(row["value"])
            for row in rows
        }
        return {
            "total_requests": metric_map.get("total_requests", 0.0),
            "failures": metric_map.get("failures", 0.0),
            "error_rate": metric_map.get("error_rate", 0.0),
            "average_latency_ms": metric_map.get("average_latency_ms", 0.0),
            "p95_latency_ms": metric_map.get("p95_latency_ms", 0.0),
            "requests_per_sec": metric_map.get("requests_per_sec", 0.0),
        }
    raise ValueError("Unsupported Locust CSV format.")


def load_scanner_summary(scanner_json_path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(scanner_json_path).read_text(encoding="utf-8"))
    summary = payload.get("summary", {})
    return {
        "scanned_files": int(summary.get("scanned_files", 0)),
        "sensitive_findings": int(summary.get("sensitive_findings", 0)),
    }


def _criterion_status(value: float | int, threshold: float | int, *, comparator: str = "<=") -> str:
    if comparator == "<=":
        return "PASS" if value <= threshold else "FAIL"
    return "PASS" if value >= threshold else "FAIL"


def generate_performance_markdown(
    locust_metrics: dict[str, float],
    scanner_summary: dict[str, Any],
    output_path: str | Path,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    criteria = [
        ("Error Rate <= 1.00%", f"{locust_metrics['error_rate']:.2f}%", "1.00%", _criterion_status(locust_metrics["error_rate"], 1.0)),
        ("p95 Latency <= 500ms", f"{locust_metrics['p95_latency_ms']:.2f} ms", "500.00 ms", _criterion_status(locust_metrics["p95_latency_ms"], 500.0)),
        ("Sensitive Findings == 0", str(scanner_summary["sensitive_findings"]), "0", "PASS" if scanner_summary["sensitive_findings"] == 0 else "FAIL"),
    ]

    lines = [
        "# Performance Report",
        "",
        f"- Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "- Scope: current internal/local benchmark and evidence scan only. This does not guarantee production performance.",
        "",
        "## Summary Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Total Requests | {int(locust_metrics['total_requests'])} |",
        f"| Failures | {int(locust_metrics['failures'])} |",
        f"| Error Rate | {locust_metrics['error_rate']:.2f}% |",
        f"| Average Latency | {locust_metrics['average_latency_ms']:.2f} ms |",
        f"| p95 Latency | {locust_metrics['p95_latency_ms']:.2f} ms |",
        f"| Requests/sec | {locust_metrics['requests_per_sec']:.2f} |",
        f"| Scanned Files | {scanner_summary['scanned_files']} |",
        f"| Sensitive Findings | {scanner_summary['sensitive_findings']} |",
        "",
        "## PASS / FAIL Criteria",
        "",
        "| Criterion | Actual | Threshold | Status |",
        "|---|---:|---:|---|",
    ]
    for criterion, actual, threshold, status in criteria:
        lines.append(f"| {criterion} | {actual} | {threshold} | {status} |")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Locust summary values come from `performance/proxy_load_stats.csv`.",
            "- Sensitive findings come from the masked JSON output of `tools/scanner.py`.",
            "- This report is intended for capstone presentation and local reproducibility evidence.",
        ]
    )
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def generate_performance_pdf(
    locust_metrics: dict[str, float],
    scanner_summary: dict[str, Any],
    output_path: str | Path,
) -> Path:
    if SimpleDocTemplate is None:
        raise ModuleNotFoundError("reportlab is required to generate PDF performance reports.")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=A4)
    styles = getSampleStyleSheet()

    criteria_rows = [
        ["Criterion", "Actual", "Threshold", "Status"],
        ["Error Rate <= 1.00%", f"{locust_metrics['error_rate']:.2f}%", "1.00%", _criterion_status(locust_metrics["error_rate"], 1.0)],
        ["p95 Latency <= 500ms", f"{locust_metrics['p95_latency_ms']:.2f} ms", "500.00 ms", _criterion_status(locust_metrics["p95_latency_ms"], 500.0)],
        ["Sensitive Findings == 0", str(scanner_summary["sensitive_findings"]), "0", "PASS" if scanner_summary["sensitive_findings"] == 0 else "FAIL"],
    ]
    summary_rows = [
        ["Metric", "Value"],
        ["Total Requests", str(int(locust_metrics["total_requests"]))],
        ["Failures", str(int(locust_metrics["failures"]))],
        ["Error Rate", f"{locust_metrics['error_rate']:.2f}%"],
        ["Average Latency", f"{locust_metrics['average_latency_ms']:.2f} ms"],
        ["p95 Latency", f"{locust_metrics['p95_latency_ms']:.2f} ms"],
        ["Requests/sec", f"{locust_metrics['requests_per_sec']:.2f}"],
        ["Scanned Files", str(scanner_summary["scanned_files"])],
        ["Sensitive Findings", str(scanner_summary["sensitive_findings"])],
    ]

    story = [
        Paragraph("Performance Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph("Current internal/local benchmark and evidence scan only. This does not guarantee production performance.", styles["BodyText"]),
        Spacer(1, 12),
        Paragraph("Summary Metrics", styles["Heading2"]),
        Spacer(1, 6),
    ]

    summary_table = Table(summary_rows, hAlign="LEFT")
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d7f3ee")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.append(summary_table)
    story.extend([Spacer(1, 14), Paragraph("PASS / FAIL Criteria", styles["Heading2"]), Spacer(1, 6)])

    criteria_table = Table(criteria_rows, hAlign="LEFT")
    criteria_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#efe6d8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    story.append(criteria_table)
    doc.build(story)
    return output


def generate_performance_reports(
    scanner_json_path: str | Path,
    locust_csv_path: str | Path,
    markdown_output_path: str | Path = "reports/performance_report.md",
    pdf_output_path: str | Path = "reports/performance_report.pdf",
) -> tuple[Path, Path]:
    scanner_summary = load_scanner_summary(scanner_json_path)
    locust_metrics = load_locust_metrics(locust_csv_path)
    markdown_path = generate_performance_markdown(locust_metrics, scanner_summary, markdown_output_path)
    pdf_path = generate_performance_pdf(locust_metrics, scanner_summary, pdf_output_path)
    return markdown_path, pdf_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate markdown or performance evidence reports.")
    parser.add_argument("--scanner-json", help="Path to scanner JSON summary for performance evidence report.")
    parser.add_argument("--locust-csv", help="Path to Locust CSV summary for performance evidence report.")
    parser.add_argument("--markdown-out", default="reports/performance_report.md", help="Output markdown report path.")
    parser.add_argument("--pdf-out", default="reports/performance_report.pdf", help="Output PDF report path.")
    args = parser.parse_args()

    if args.scanner_json and args.locust_csv:
        markdown_path, pdf_path = generate_performance_reports(
            args.scanner_json,
            args.locust_csv,
            markdown_output_path=args.markdown_out,
            pdf_output_path=args.pdf_out,
        )
        print(f"Markdown report saved to: {markdown_path}")
        print(f"PDF report saved to: {pdf_path}")
        return

    parser.error("Provide both --scanner-json and --locust-csv to generate performance reports.")


if __name__ == "__main__":
    main()
