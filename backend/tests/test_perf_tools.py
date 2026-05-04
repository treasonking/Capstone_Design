from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from evaluation import report_generator


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCANNER_PATH = PROJECT_ROOT / "tools" / "scanner.py"


def _load_scanner_module():
    spec = importlib.util.spec_from_file_location("scanner_module", SCANNER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_scanner_masks_findings_in_json(tmp_path) -> None:
    scanner_module = _load_scanner_module()
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "sample.log"
    log_file.write_text("연락처는 010-1234-5678 입니다. 메일은 alice@example.com 입니다.", encoding="utf-8")

    result = {
        "summary": {"scanned_files": 1, "sensitive_findings": 2, "include_reports": False},
        "findings": [
            {
                "path": "logs/sample.log",
                "reason_code": "PII_PHONE_DETECTED",
                "category": "PHONE",
                "score": 0.9,
                "masked_match": "010-12**-****",
                "masked_excerpt": "연락처는 010-12**-**** 입니다.",
            },
            {
                "path": "logs/sample.log",
                "reason_code": "PII_EMAIL_DETECTED",
                "category": "EMAIL",
                "score": 0.95,
                "masked_match": "al***@example.com",
                "masked_excerpt": "메일은 al***@example.com 입니다.",
            },
        ],
    }
    output = tmp_path / "scanner_result.json"
    scanner_module.write_json_report(result, output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "010-1234-5678" not in serialized
    assert "alice@example.com" not in serialized
    assert "010-12**-****" in serialized


def test_scanner_skips_numeric_only_locust_history_rows(tmp_path) -> None:
    scanner_module = _load_scanner_module()
    history_csv = tmp_path / "proxy_load_stats_history.csv"
    history_csv.write_text(
        "\n".join(
            [
                "Timestamp,User Count,Type,Name,Requests/s,Failures/s,Total Average Response Time",
                "1777798464,0,,Aggregated,0.000000,0.000000,0.0",
                "1777798465,5,,Aggregated,0.000000,0.000000,406.0575400071684",
            ]
        ),
        encoding="utf-8",
    )

    scanned_text = scanner_module._read_text(history_csv)
    assert scanned_text == ""


def test_performance_report_contains_pass_fail_table(tmp_path) -> None:
    scanner_json = tmp_path / "scanner_result.json"
    scanner_json.write_text(
        json.dumps({"summary": {"scanned_files": 3, "sensitive_findings": 0}, "findings": []}, ensure_ascii=False),
        encoding="utf-8",
    )

    locust_csv = tmp_path / "proxy_load_stats.csv"
    locust_csv.write_text(
        "\n".join(
            [
                "metric,value",
                "total_requests,1000",
                "failures,5",
                "error_rate,0.50",
                "average_latency_ms,120.0",
                "p95_latency_ms,320.0",
                "requests_per_sec,40.0",
            ]
        ),
        encoding="utf-8",
    )

    markdown_path = tmp_path / "performance_report.md"
    report_generator.generate_performance_markdown(
        report_generator.load_locust_metrics(locust_csv),
        report_generator.load_scanner_summary(scanner_json),
        markdown_path,
    )

    content = markdown_path.read_text(encoding="utf-8")
    assert "## PASS / FAIL Criteria" in content
    assert "| Error Rate <= 1.00% | 0.50% | 1.00% | PASS |" in content
