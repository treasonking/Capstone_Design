from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "audit_log.jsonl"


def _build_log_entry(
    request_id: str,
    user_id: str,
    audit_summary: dict[str, Any],
) -> dict[str, Any]:
    input_summary = audit_summary.get("input") or {}
    output_summary = audit_summary.get("output") or {}

    return {
        "request_id": request_id,
        "user_id": user_id,
        "timestamp": audit_summary.get("timestamp_utc"),
        "action": audit_summary.get("action"),
        "reason_codes": audit_summary.get("reason_codes", []),
        "pii_detected": bool(input_summary.get("pii_detected")) or bool(output_summary.get("pii_detected")),
        "injection_detected": bool(input_summary.get("injection_detected")) or bool(output_summary.get("injection_detected")),
        "latency_ms": audit_summary.get("latency_ms"),
        "upstream_call": bool(audit_summary.get("upstream_call")),
        "input_action": audit_summary.get("input_action"),
        "output_action": audit_summary.get("output_action"),
    }


def save_audit_log(
    request_id: str,
    user_id: str,
    audit_summary: dict[str, Any],
) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_entry = _build_log_entry(request_id, user_id, audit_summary)
    with LOG_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
