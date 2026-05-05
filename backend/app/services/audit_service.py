from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "audit_log.jsonl"


def _merge_counts(*values: dict[str, Any]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for value in values:
        for key, amount in value.items():
            try:
                counter[str(key)] += int(amount)
            except (TypeError, ValueError):
                continue
    return dict(counter)


def _build_log_entry(
    request_id: str,
    user_id: str,
    audit_summary: dict[str, Any],
) -> dict[str, Any]:
    input_summary = audit_summary.get("input") or {}
    output_summary = audit_summary.get("output") or {}
    detector_counts = _merge_counts(
        input_summary.get("detector_counts", {}) or {},
        output_summary.get("detector_counts", {}) or {},
    )

    return {
        "request_id": request_id,
        "user_id": user_id,
        "timestamp": audit_summary.get("timestamp_utc"),
        "action": audit_summary.get("action"),
        "reason_codes": audit_summary.get("reason_codes", []),
        "reason_code": (audit_summary.get("reason_codes") or [None])[0],
        "pii_detected": bool(input_summary.get("pii_detected")) or bool(output_summary.get("pii_detected")),
        "injection_detected": bool(input_summary.get("injection_detected")) or bool(output_summary.get("injection_detected")),
        "model_detected": bool(input_summary.get("model_detected")) or bool(output_summary.get("model_detected")),
        "latency_ms": audit_summary.get("latency_ms"),
        "upstream_call": bool(audit_summary.get("upstream_call")),
        "input_action": audit_summary.get("input_action"),
        "output_action": audit_summary.get("output_action"),
        "detector_counts": detector_counts,
        "policy_version": audit_summary.get("policy_version"),
        "model_version": audit_summary.get("model_version"),
        "masked_preview": input_summary.get("masked_preview") or output_summary.get("masked_preview"),
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
    entries = read_audit_logs()
    action_counts = Counter(entry.get("action", "UNKNOWN") for entry in entries)
    detector_type_counts = {
        "pii": sum(1 for entry in entries if entry.get("pii_detected")),
        "injection": sum(1 for entry in entries if entry.get("injection_detected")),
        "model": sum(1 for entry in entries if entry.get("model_detected")),
    }

    latencies = [float(entry["latency_ms"]) for entry in entries if entry.get("latency_ms") not in (None, "")]
    average_latency_ms = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
    today_utc = datetime.now(timezone.utc).date()
    today_entries = [
        entry
        for entry in entries
        if entry.get("timestamp") and datetime.fromisoformat(str(entry["timestamp"]).replace("Z", "+00:00")).date() == today_utc
    ]
    today_actions = Counter(entry.get("action", "UNKNOWN") for entry in today_entries)

    return {
        "total_requests": len(entries),
        "blocked_requests": action_counts.get("BLOCK", 0),
        "masked_requests": action_counts.get("MASK", 0),
        "warned_requests": action_counts.get("WARN", 0),
        "allowed_requests": action_counts.get("ALLOW", 0),
        "error_requests": action_counts.get("ERROR", 0),
        "detection_type_counts": detector_type_counts,
        "average_latency_ms": average_latency_ms,
        "today_blocked_requests": today_actions.get("BLOCK", 0),
        "today_masked_requests": today_actions.get("MASK", 0),
        "today_warned_requests": today_actions.get("WARN", 0),
    }


def get_recent_block_history(limit: int = 10) -> list[dict[str, Any]]:
    blocked_entries = [entry for entry in read_audit_logs() if entry.get("action") == "BLOCK"]
    recent_entries = blocked_entries[-limit:]
    recent_entries.reverse()
    return recent_entries


def get_reason_code_stats() -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for entry in read_audit_logs():
        for reason_code in entry.get("reason_codes", []):
            counter[reason_code] += 1

    return [{"reason_code": reason_code, "count": count} for reason_code, count in counter.most_common()]


def get_audit_log_history(limit: int = 20) -> list[dict[str, Any]]:
    entries = read_audit_logs(limit=limit)
    entries.reverse()
    return entries
