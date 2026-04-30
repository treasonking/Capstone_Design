from __future__ import annotations

import json
from collections import Counter
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

    # Persist only metadata needed for audit and admin statistics.
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


def read_audit_logs(limit: int | None = None) -> list[dict[str, Any]]:
    # JSONL is used so each request can be appended independently without
    # rewriting the entire log file.
    if not LOG_FILE.exists():
        return []

    entries: list[dict[str, Any]] = []
    with LOG_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))

    if limit is None or limit >= len(entries):
        return entries
    return entries[-limit:]


def get_admin_stats() -> dict[str, Any]:
    # Precompute counts in the backend so the admin UI can stay simple.
    entries = read_audit_logs()
    action_counts = Counter(entry.get("action", "UNKNOWN") for entry in entries)

    detection_type_counts = {
        "pii": sum(1 for entry in entries if entry.get("pii_detected")),
        "injection": sum(1 for entry in entries if entry.get("injection_detected")),
    }

    return {
        "total_requests": len(entries),
        "blocked_requests": action_counts.get("BLOCK", 0),
        "masked_requests": action_counts.get("MASK", 0),
        "warned_requests": action_counts.get("WARN", 0),
        "allowed_requests": action_counts.get("ALLOW", 0),
        "error_requests": action_counts.get("ERROR", 0),
        "detection_type_counts": detection_type_counts,
    }


def get_recent_block_history(limit: int = 10) -> list[dict[str, Any]]:
    # Return the newest blocked events first for the admin activity table.
    blocked_entries = [entry for entry in read_audit_logs() if entry.get("action") == "BLOCK"]
    recent_entries = blocked_entries[-limit:]
    recent_entries.reverse()
    return recent_entries


def get_reason_code_stats() -> list[dict[str, Any]]:
    # Reason-code frequency powers the "top detection reasons" widget.
    counter: Counter[str] = Counter()
    for entry in read_audit_logs():
        for reason_code in entry.get("reason_codes", []):
            counter[reason_code] += 1

    return [
        {"reason_code": reason_code, "count": count}
        for reason_code, count in counter.most_common()
    ]
