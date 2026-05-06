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

    # 감사와 관리자 통계에 필요한 메타데이터만 저장합니다.
    entry = {
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
        "detector_counts": {
            "input": input_summary.get("detector_counts", {}),
            "output": output_summary.get("detector_counts", {}),
        },
    }
    hybrid_detection = audit_summary.get("hybrid_detection")
    if hybrid_detection is not None:
        entry["hybrid_detection"] = hybrid_detection
    return entry


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
    # JSONL 형식을 사용하면 전체 파일을 다시 쓰지 않고 요청별 로그를 한 줄씩 추가할 수 있습니다.
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
    # 관리자 화면이 단순하게 표시만 할 수 있도록 백엔드에서 집계를 미리 계산합니다.
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
    # 관리자 최근 이력 테이블에서 바로 쓰도록 최신 차단 이벤트를 먼저 반환합니다.
    blocked_entries = [entry for entry in read_audit_logs() if entry.get("action") == "BLOCK"]
    recent_entries = blocked_entries[-limit:]
    recent_entries.reverse()
    return recent_entries


def get_reason_code_stats() -> list[dict[str, Any]]:
    # reason_code 빈도는 탐지 사유 통계 위젯에서 사용됩니다.
    counter: Counter[str] = Counter()
    for entry in read_audit_logs():
        for reason_code in entry.get("reason_codes", []):
            counter[reason_code] += 1

    return [
        {"reason_code": reason_code, "count": count}
        for reason_code, count in counter.most_common()
    ]
