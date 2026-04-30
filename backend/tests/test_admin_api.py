from __future__ import annotations

import asyncio
import json

from backend.app.api.proxy import admin_reason_codes, admin_recent_blocks, admin_stats
from backend.app.services import audit_service


def _write_logs(tmp_path, entries: list[dict]) -> None:
    # Seed a temporary JSONL log file so admin endpoints can be tested offline.
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "audit_log.jsonl"
    with log_file.open("w", encoding="utf-8") as file:
        for entry in entries:
            file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def test_admin_stats_returns_aggregate_counts(tmp_path, monkeypatch) -> None:
    # The stats endpoint should collapse raw audit logs into dashboard counters.
    log_file = tmp_path / "logs" / "audit_log.jsonl"
    _write_logs(
        tmp_path,
        [
            {
                "request_id": "req-1",
                "user_id": "u1",
                "timestamp": "2026-04-30T00:00:00Z",
                "action": "BLOCK",
                "reason_codes": ["INJ_DIRECT_OVERRIDE_ATTEMPT"],
                "pii_detected": False,
                "injection_detected": True,
                "latency_ms": 5,
                "upstream_call": False,
                "input_action": "BLOCK",
                "output_action": None,
            },
            {
                "request_id": "req-2",
                "user_id": "u2",
                "timestamp": "2026-04-30T00:01:00Z",
                "action": "MASK",
                "reason_codes": ["PII_PHONE_DETECTED"],
                "pii_detected": True,
                "injection_detected": False,
                "latency_ms": 7,
                "upstream_call": True,
                "input_action": "MASK",
                "output_action": "ALLOW",
            },
            {
                "request_id": "req-3",
                "user_id": "u3",
                "timestamp": "2026-04-30T00:02:00Z",
                "action": "ALLOW",
                "reason_codes": ["SAFE_INPUT"],
                "pii_detected": False,
                "injection_detected": False,
                "latency_ms": 3,
                "upstream_call": True,
                "input_action": "ALLOW",
                "output_action": "ALLOW",
            },
        ],
    )
    monkeypatch.setattr(audit_service, "LOG_FILE", log_file)

    result = asyncio.run(admin_stats())

    assert result.total_requests == 3
    assert result.blocked_requests == 1
    assert result.masked_requests == 1
    assert result.allowed_requests == 1
    assert result.detection_type_counts["pii"] == 1
    assert result.detection_type_counts["injection"] == 1


def test_admin_recent_blocks_returns_latest_first(tmp_path, monkeypatch) -> None:
    # Recent block history should show newest blocked events first.
    log_file = tmp_path / "logs" / "audit_log.jsonl"
    _write_logs(
        tmp_path,
        [
            {
                "request_id": "req-1",
                "user_id": "u1",
                "timestamp": "2026-04-30T00:00:00Z",
                "action": "BLOCK",
                "reason_codes": ["R1"],
                "pii_detected": False,
                "injection_detected": True,
                "latency_ms": 5,
                "upstream_call": False,
                "input_action": "BLOCK",
                "output_action": None,
            },
            {
                "request_id": "req-2",
                "user_id": "u2",
                "timestamp": "2026-04-30T00:01:00Z",
                "action": "ALLOW",
                "reason_codes": ["SAFE_INPUT"],
                "pii_detected": False,
                "injection_detected": False,
                "latency_ms": 3,
                "upstream_call": True,
                "input_action": "ALLOW",
                "output_action": "ALLOW",
            },
            {
                "request_id": "req-3",
                "user_id": "u3",
                "timestamp": "2026-04-30T00:02:00Z",
                "action": "BLOCK",
                "reason_codes": ["R2"],
                "pii_detected": True,
                "injection_detected": False,
                "latency_ms": 8,
                "upstream_call": True,
                "input_action": "MASK",
                "output_action": "BLOCK",
            },
        ],
    )
    monkeypatch.setattr(audit_service, "LOG_FILE", log_file)

    result = asyncio.run(admin_recent_blocks())

    assert len(result) == 2
    assert result[0].request_id == "req-3"
    assert result[1].request_id == "req-1"


def test_admin_reason_codes_returns_frequency_stats(tmp_path, monkeypatch) -> None:
    # Reason-code stats should be sorted by descending frequency.
    log_file = tmp_path / "logs" / "audit_log.jsonl"
    _write_logs(
        tmp_path,
        [
            {
                "request_id": "req-1",
                "user_id": "u1",
                "timestamp": "2026-04-30T00:00:00Z",
                "action": "BLOCK",
                "reason_codes": ["R1", "R2"],
                "pii_detected": False,
                "injection_detected": True,
                "latency_ms": 5,
                "upstream_call": False,
                "input_action": "BLOCK",
                "output_action": None,
            },
            {
                "request_id": "req-2",
                "user_id": "u2",
                "timestamp": "2026-04-30T00:01:00Z",
                "action": "MASK",
                "reason_codes": ["R2"],
                "pii_detected": True,
                "injection_detected": False,
                "latency_ms": 7,
                "upstream_call": True,
                "input_action": "MASK",
                "output_action": "ALLOW",
            },
        ],
    )
    monkeypatch.setattr(audit_service, "LOG_FILE", log_file)

    result = asyncio.run(admin_reason_codes())

    assert result[0].reason_code == "R2"
    assert result[0].count == 2
    assert result[1].reason_code == "R1"
    assert result[1].count == 1
