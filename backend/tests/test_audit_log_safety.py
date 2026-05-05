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


def test_audit_log_redacts_authorization_and_pii(tmp_path, monkeypatch) -> None:
    log_dir = tmp_path / "logs"
    log_file = log_dir / "audit_log.jsonl"
    monkeypatch.setattr(audit_service, "LOG_DIR", log_dir)
    monkeypatch.setattr(audit_service, "LOG_FILE", log_file)
    monkeypatch.setattr(llm_service.httpx, "AsyncClient", _build_fake_client({"choices": [{"message": {"content": "ok"}}]}))

    prompt = "Authorization: Bearer super-secret-token 연락처는 010-1234-5678 입니다."
    asyncio.run(proxy_chat(ProxyRequest(message=prompt)))

    payload = json.loads(log_file.read_text(encoding="utf-8").splitlines()[0])
    serialized = json.dumps(payload, ensure_ascii=False)

    assert "super-secret-token" not in serialized
    assert "010-1234-5678" not in serialized
    assert payload["masked_preview"] is not None
