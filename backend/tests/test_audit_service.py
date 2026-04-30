from __future__ import annotations

import asyncio
import json

import httpx

from backend.app.api.proxy import ProxyRequest, proxy_chat
from backend.app.services import audit_service, llm_service


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self._status_code = status_code

    def raise_for_status(self) -> None:
        if self._status_code >= 400:
            request = httpx.Request("POST", "http://test")
            response = httpx.Response(self._status_code, request=request)
            raise httpx.HTTPStatusError("upstream error", request=request, response=response)

    def json(self) -> dict:
        return self._payload


def _build_fake_client(payload: dict, status_code: int = 200):
    # 감사 로그 테스트가 항상 같은 결과를 내도록 가짜 upstream을 사용합니다.
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            self._payload = payload
            self._status_code = status_code

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *args, **kwargs):
            return _FakeResponse(self._payload, self._status_code)

    return _FakeAsyncClient


def test_build_log_entry_keeps_metadata_only() -> None:
    # 감사 로그 항목에는 원문 프롬프트나 원문 응답 필드가 복사되면 안 됩니다.
    audit_summary = {
        "timestamp_utc": "2026-04-30T00:00:00Z",
        "action": "MASK",
        "reason_codes": ["PII_PHONE_DETECTED"],
        "latency_ms": 12.3,
        "upstream_call": True,
        "input_action": "MASK",
        "output_action": "ALLOW",
        "input": {
            "pii_detected": True,
            "injection_detected": False,
            "raw_prompt": "010-1234-5678",
        },
        "output": {
            "pii_detected": False,
            "injection_detected": False,
            "raw_response": "normal response",
        },
    }

    entry = audit_service._build_log_entry("req-1", "user-1", audit_summary)

    assert entry["request_id"] == "req-1"
    assert entry["user_id"] == "user-1"
    assert entry["action"] == "MASK"
    assert entry["reason_codes"] == ["PII_PHONE_DETECTED"]
    assert entry["pii_detected"] is True
    assert entry["injection_detected"] is False
    assert "raw_prompt" not in entry
    assert "raw_response" not in entry


def test_save_audit_log_writes_jsonl_without_raw_fields(tmp_path) -> None:
    # 저장된 로그는 올바른 JSONL이어야 하며 안전한 메타데이터만 포함해야 합니다.
    log_dir = tmp_path / "logs"
    log_file = log_dir / "audit_log.jsonl"
    audit_service.LOG_DIR = log_dir
    audit_service.LOG_FILE = log_file

    audit_service.save_audit_log(
        "req-2",
        "user-2",
        {
            "timestamp_utc": "2026-04-30T00:00:00Z",
            "action": "ALLOW",
            "reason_codes": ["SAFE_INPUT"],
            "latency_ms": 4.2,
            "upstream_call": True,
            "input_action": "ALLOW",
            "output_action": "ALLOW",
            "input": {"pii_detected": False, "injection_detected": False},
            "output": {"pii_detected": False, "injection_detected": False},
        },
    )

    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["request_id"] == "req-2"
    assert entry["action"] == "ALLOW"
    assert entry["upstream_call"] is True
    assert "content" not in entry
    assert "prompt" not in entry


def test_proxy_chat_audit_log_excludes_raw_prompt_and_response(tmp_path, monkeypatch) -> None:
    # 프록시 전체 흐름을 거쳐도 정제된 감사 로그만 저장되어야 합니다.
    log_dir = tmp_path / "logs"
    log_file = log_dir / "audit_log.jsonl"
    monkeypatch.setattr(audit_service, "LOG_DIR", log_dir)
    monkeypatch.setattr(audit_service, "LOG_FILE", log_file)
    payload = {"choices": [{"message": {"content": "normal response"}}]}
    monkeypatch.setattr(llm_service.httpx, "AsyncClient", _build_fake_client(payload))

    prompt = "My phone number is 010-1234-5678"
    result = asyncio.run(proxy_chat(ProxyRequest(message=prompt)))

    assert result.request_id
    assert result.audit_summary["action"] == "MASK"

    entry = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    assert entry["request_id"] == result.request_id
    assert entry["action"] == "MASK"
    assert entry["upstream_call"] is True
    assert "reason_codes" in entry
    assert prompt not in json.dumps(entry, ensure_ascii=False)
    assert "normal response" not in json.dumps(entry, ensure_ascii=False)
