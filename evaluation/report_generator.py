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

# ---------------------------------------------------------------------------
# Performance / evidence PDF report generation
# ---------------------------------------------------------------------------


def _load_scanner_result(scanner_json_path: str | Path) -> dict[str, Any]:
    import json

    path = Path(scanner_json_path)
    if not path.exists():
        return {
            "status": "UNKNOWN",
            "sensitive_findings_count": None,
            "log_findings_count": None,
            "db_findings_count": None,
            "findings": [],
            "missing_input": str(path),
        }
    return json.loads(path.read_text(encoding="utf-8"))


def _find_locust_stats_csv(search_root: str | Path) -> Path | None:
    root = Path(search_root)
    candidates = sorted(root.rglob("*_stats.csv"), key=lambda item: item.stat().st_mtime, reverse=True)
    for candidate in candidates:
        if not candidate.name.endswith("_stats_history.csv") and not candidate.name.endswith("_failures.csv"):
            return candidate
    return None


def _load_locust_metrics(locust_csv_path: str | Path | None, search_root: str | Path) -> dict[str, Any]:
    if locust_csv_path is None:
        locust_path = _find_locust_stats_csv(search_root)
    else:
        locust_path = Path(locust_csv_path)

    if locust_path is None or not locust_path.exists():
        return {
            "status": "UNKNOWN",
            "csv_path": None if locust_path is None else str(locust_path),
            "p95_latency_ms": None,
            "tps": None,
            "error_rate_percent": None,
            "request_count": None,
            "failure_count": None,
        }

    try:
        import pandas as pd
    except ImportError as exc:
        raise SystemExit("pandas is required. Install with: pip install pandas reportlab") from exc

    frame = pd.read_csv(locust_path)
    if frame.empty:
        return {
            "status": "UNKNOWN",
            "csv_path": str(locust_path),
            "p95_latency_ms": None,
            "tps": None,
            "error_rate_percent": None,
            "request_count": None,
            "failure_count": None,
        }

    name_column = "Name" if "Name" in frame.columns else None
    if name_column and (frame[name_column] == "Aggregated").any():
        row = frame.loc[frame[name_column] == "Aggregated"].iloc[0]
    else:
        row = frame.iloc[-1]

    request_count = float(row.get("Request Count", 0) or 0)
    failure_count = float(row.get("Failure Count", 0) or 0)
    p95_column = "95%" if "95%" in frame.columns else "95"
    p95_latency_ms = float(row.get(p95_column, 0) or 0) if p95_column in frame.columns else None
    tps = float(row.get("Requests/s", 0) or 0) if "Requests/s" in frame.columns else None
    error_rate = (failure_count / request_count * 100) if request_count else None

    return {
        "status": "LOADED",
        "csv_path": str(locust_path),
        "p95_latency_ms": p95_latency_ms,
        "tps": tps,
        "error_rate_percent": error_rate,
        "request_count": int(request_count),
        "failure_count": int(failure_count),
    }


def _pass_fail(value: bool | None) -> str:
    if value is None:
        return "UNKNOWN"
    return "PASS" if value else "FAIL"


def _build_performance_judgement(
    scanner_result: dict[str, Any],
    locust_metrics: dict[str, Any],
    p95_threshold_ms: float,
    error_rate_threshold_percent: float,
) -> dict[str, Any]:
    sensitive_count = scanner_result.get("sensitive_findings_count")
    p95_latency = locust_metrics.get("p95_latency_ms")
    error_rate = locust_metrics.get("error_rate_percent")

    scanner_pass = None if sensitive_count is None else int(sensitive_count) == 0
    latency_pass = None if p95_latency is None else float(p95_latency) <= p95_threshold_ms
    error_rate_pass = None if error_rate is None else float(error_rate) <= error_rate_threshold_percent
    overall_pass = all(item is True for item in [scanner_pass, latency_pass, error_rate_pass])

    return {
        "scanner_pass": scanner_pass,
        "latency_pass": latency_pass,
        "error_rate_pass": error_rate_pass,
        "overall_status": "PASS" if overall_pass else "FAIL",
        "p95_threshold_ms": p95_threshold_ms,
        "error_rate_threshold_percent": error_rate_threshold_percent,
    }


def _register_pdf_font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/NanumGothic.ttf"),
        Path("/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            pdfmetrics.registerFont(TTFont("EvidenceFont", str(candidate)))
            return "EvidenceFont"
    return "Helvetica"


def generate_performance_pdf_report(
    scanner_json_path: str | Path = Path("reports") / "scanner_result.json",
    locust_csv_path: str | Path | None = None,
    output_path: str | Path = Path("reports") / "performance_report.pdf",
    *,
    p95_threshold_ms: float = 500.0,
    error_rate_threshold_percent: float = 1.0,
    search_root: str | Path = ".",
) -> Path:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise SystemExit("reportlab is required. Install with: pip install pandas reportlab") from exc

    scanner_result = _load_scanner_result(scanner_json_path)
    locust_metrics = _load_locust_metrics(locust_csv_path, search_root)
    judgement = _build_performance_judgement(
        scanner_result,
        locust_metrics,
        p95_threshold_ms,
        error_rate_threshold_percent,
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    font_name = _register_pdf_font()
    styles = getSampleStyleSheet()
    for style_name in ["Title", "Heading1", "Heading2", "BodyText"]:
        styles[style_name].fontName = font_name
    styles["Title"].fontSize = 18
    styles["Heading1"].fontSize = 13
    styles["BodyText"].fontSize = 9

    doc = SimpleDocTemplate(str(output), pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    story: list[Any] = []

    story.append(Paragraph("LLM Security Proxy MVP Performance Evidence Report", styles["Title"]))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(f"Generated at: {datetime.now().isoformat(timespec='seconds')}", styles["BodyText"]))
    story.append(Paragraph(f"Overall Status: {judgement['overall_status']}", styles["Heading1"]))
    story.append(Spacer(1, 4 * mm))

    summary_rows = [
        ["Check", "Measured Value", "Criteria", "Result"],
        [
            "Raw sensitive data in logs/DB",
            str(scanner_result.get("sensitive_findings_count", "UNKNOWN")),
            "0 findings",
            _pass_fail(judgement["scanner_pass"]),
        ],
        [
            "p95 latency",
            "UNKNOWN" if locust_metrics.get("p95_latency_ms") is None else f"{locust_metrics['p95_latency_ms']:.2f} ms",
            f"<= {p95_threshold_ms:.0f} ms",
            _pass_fail(judgement["latency_pass"]),
        ],
        [
            "Error rate",
            "UNKNOWN" if locust_metrics.get("error_rate_percent") is None else f"{locust_metrics['error_rate_percent']:.2f}%",
            f"<= {error_rate_threshold_percent:.2f}%",
            _pass_fail(judgement["error_rate_pass"]),
        ],
    ]
    table = Table(summary_rows, colWidths=[48 * mm, 42 * mm, 38 * mm, 28 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7fafb")),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 7 * mm))

    story.append(Paragraph("Scanner Evidence", styles["Heading1"]))
    story.append(Paragraph(f"Scanner JSON: {scanner_json_path}", styles["BodyText"]))
    story.append(Paragraph(f"Log findings: {scanner_result.get('log_findings_count', 'UNKNOWN')}", styles["BodyText"]))
    story.append(Paragraph(f"DB findings: {scanner_result.get('db_findings_count', 'UNKNOWN')}", styles["BodyText"]))

    findings = scanner_result.get("findings") or []
    if findings:
        finding_rows = [["Source", "Location", "Pattern", "Excerpt"]]
        for finding in findings[:10]:
            finding_rows.append(
                [
                    str(finding.get("source", "")),
                    f"{finding.get('path', '')}:{finding.get('line', '')}",
                    str(finding.get("pattern", "")),
                    str(finding.get("excerpt", ""))[:80],
                ]
            )
        finding_table = Table(finding_rows, colWidths=[22 * mm, 46 * mm, 34 * mm, 54 * mm])
        finding_table.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), font_name), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8a1f1f")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]))
        story.append(Spacer(1, 3 * mm))
        story.append(finding_table)
    else:
        story.append(Paragraph("No unmasked sensitive values were found in scanned targets.", styles["BodyText"]))

    story.append(Spacer(1, 7 * mm))
    story.append(Paragraph("Locust Evidence", styles["Heading1"]))
    story.append(Paragraph(f"Locust CSV: {locust_metrics.get('csv_path') or 'not found'}", styles["BodyText"]))
    story.append(Paragraph(f"TPS: {locust_metrics.get('tps', 'UNKNOWN')}", styles["BodyText"]))
    story.append(Paragraph(f"Requests / Failures: {locust_metrics.get('request_count', 'UNKNOWN')} / {locust_metrics.get('failure_count', 'UNKNOWN')}", styles["BodyText"]))

    doc.build(story)
    return output


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Generate PASS/FAIL PDF evidence report from scanner and Locust CSV outputs.")
    parser.add_argument("--scanner-json", default=str(Path("reports") / "scanner_result.json"))
    parser.add_argument("--locust-csv", default=None, help="Path to Locust *_stats.csv. If omitted, newest *_stats.csv is used.")
    parser.add_argument("--output", default=str(Path("reports") / "performance_report.pdf"))
    parser.add_argument("--p95-threshold-ms", type=float, default=500.0)
    parser.add_argument("--error-rate-threshold-percent", type=float, default=1.0)
    parser.add_argument("--search-root", default=".")
    args = parser.parse_args()

    output = generate_performance_pdf_report(
        scanner_json_path=args.scanner_json,
        locust_csv_path=args.locust_csv,
        output_path=args.output,
        p95_threshold_ms=args.p95_threshold_ms,
        error_rate_threshold_percent=args.error_rate_threshold_percent,
        search_root=args.search_root,
    )
    print(f"PDF report generated: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
