from __future__ import annotations

import asyncio

import httpx

from backend.app.services import llm_service


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


def test_split_model_target_for_openai() -> None:
    # Prefixed model strings should split cleanly into provider and model name.
    provider, model = llm_service._split_model_target("openai:gpt-4o-mini")

    assert provider == "openai"
    assert model == "gpt-4o-mini"


def test_build_openai_request_includes_bearer_header(monkeypatch) -> None:
    # OpenAI requests should carry a bearer token and explicit model field.
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(llm_service, "DEFAULT_OPENAI_MODEL", "gpt-4o-mini")

    url, headers, payload = llm_service._build_request("openai", "hello", "openai:gpt-4o-mini")

    assert url.endswith("/v1/chat/completions")
    assert headers["Authorization"] == "Bearer test-openai-key"
    assert payload["model"] == "gpt-4o-mini"
    assert payload["messages"][0]["content"] == "hello"


def test_build_azure_request_adds_api_version(monkeypatch) -> None:
    # Azure OpenAI uses deployment-specific URLs plus api-version query params.
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-azure-key")
    monkeypatch.setattr(llm_service, "DEFAULT_AZURE_API_VERSION", "2024-02-15-preview")
    monkeypatch.setattr(llm_service, "_PROVIDER_URLS", {
        **llm_service._PROVIDER_URLS,
        "azure": "https://example.openai.azure.com/openai/deployments/my-deployment/chat/completions",
    })

    url, headers, payload = llm_service._build_request("azure", "hello", "azure:my-deployment")

    assert "api-version=2024-02-15-preview" in url
    assert headers["api-key"] == "test-azure-key"
    assert "model" not in payload
    assert payload["messages"][0]["content"] == "hello"


def test_extract_ollama_content() -> None:
    # Ollama responses store assistant text under message.content.
    content = llm_service._extract_content("ollama", {"message": {"content": "ollama reply"}})

    assert content == "ollama reply"


def test_call_upstream_llm_uses_ollama_prefixed_model(monkeypatch) -> None:
    # Provider-prefixed models should be converted into the correct Ollama payload.
    captured: dict[str, object] = {}

    class _InspectAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _FakeResponse({"message": {"content": "ollama ok"}})

    monkeypatch.setattr(llm_service.httpx, "AsyncClient", _InspectAsyncClient)

    content = asyncio.run(llm_service.call_upstream_llm("hello", model="ollama:llama3.1"))

    assert content == "ollama ok"
    assert captured["json"]["model"] == "llama3.1"
    assert captured["json"]["stream"] is False


def test_call_upstream_llm_uses_openai_prefixed_model(monkeypatch) -> None:
    # Provider-prefixed models should also work for OpenAI-style upstreams.
    captured: dict[str, object] = {}

    class _InspectAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json, headers):
            captured["url"] = url
            captured["json"] = json
            captured["headers"] = headers
            return _FakeResponse({"choices": [{"message": {"content": "openai ok"}}]})

    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(llm_service.httpx, "AsyncClient", _InspectAsyncClient)

    content = asyncio.run(llm_service.call_upstream_llm("hello", model="openai:gpt-4o-mini"))

    assert content == "openai ok"
    assert captured["json"]["model"] == "gpt-4o-mini"
    assert captured["headers"]["Authorization"] == "Bearer test-openai-key"
