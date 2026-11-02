"""Internal corpus/routing and guarded API regression, not live LLM accuracy."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.api.proxy import app
from backend.app.providers.base import ProviderResponse
from backend.app.schemas.proxy import ProxyRequest
from backend.app.services import audit_service, proxy_service, resident_center_agent
from backend.app.services.auth_service import issue_token
from backend.app.services.conversation import conversation_input

SCENARIOS = json.loads((Path(__file__).resolve().parents[2] /
    "evaluation/datasets/resident_center_expansion_scenarios.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["id"] for s in SCENARIOS])
def test_expanded_corpus_and_guarded_chat(scenario, monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_MODEL_DETECTOR", "false")
    monkeypatch.setenv("USER_POLICY_ID", "default")
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr(audit_service, "LOG_FILE", log)
    calls = []
    output = scenario.get("provider_output", "공개자료를 참고한 안내입니다.")

    async def provider(message, **options):
        calls.append({"input": message, **options})
        return ProviderResponse(text=output, provider="openai", model="synthetic-test", latency_ms=0)

    monkeypatch.setattr(proxy_service, "generate_upstream_response", provider)
    body = {"message": scenario["message"], "history": scenario.get("history", []), "assistant": "resident_center"}
    # A correct document must rank first, rather than merely appear in top three.
    if scenario["kind"] in {"retrieval", "followup", "unsupported"}:
        docs = resident_center_agent.search_services(conversation_input(ProxyRequest(**body)))
        assert (docs[0]["id"] if docs else None) == scenario.get("source")
    client = TestClient(app, headers={"Authorization": f"Bearer {issue_token('expanded-test@example.com')}"})
    assert client.post("/proxy/analyze", json=body).status_code == 200
    assert calls == []
    response = client.post("/proxy/chat", json=body)
    assert response.status_code == 200
    result = response.json()
    assert result["action"] == scenario["action"]
    assert bool(calls) == scenario.get("provider_called", True)
    if result["action"] == "BLOCK":
        assert result["content"] is None
    elif scenario.get("source"):
        assert f'[{scenario["source"]}]' in result["content"]
        instructions = calls[0]["system_instructions"]
        supplied = json.loads(instructions.split("공개 참고자료(JSON):\n", 1)[1])
        assert scenario["source"] in {doc["id"] for doc in supplied}
        if scenario["kind"] in {"retrieval", "followup"}:
            assert supplied[0]["id"] == scenario["source"]
    else:
        assert "근거자료가 없습니다" in result["content"]
        assert calls[0]["system_instructions"].endswith("공개 참고자료(JSON):\n[]")
    secret = scenario.get("secret")
    if secret:
        if not scenario.get("output_secret"):
            assert secret not in str(calls)
        assert secret not in (result["content"] or "")
        assert secret not in log.read_text(encoding="utf-8")
    saved = log.read_text(encoding="utf-8")
    assert scenario["message"] not in saved
    assert output not in saved
    if calls:
        assert calls[0]["system_instructions"] not in saved
