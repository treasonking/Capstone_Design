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
    # provider:model 형식은 제공자와 모델 이름으로 정확히 분리되어야 합니다.
    provider, model = llm_service._split_model_target("openai:gpt-4o-mini")

    assert provider == "openai"
    assert model == "gpt-4o-mini"


def test_build_openai_request_includes_bearer_header(monkeypatch) -> None:
    # OpenAI 요청에는 Bearer 토큰과 명시적인 model 필드가 포함되어야 합니다.
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setattr(llm_service, "DEFAULT_OPENAI_MODEL", "gpt-4o-mini")

    url, headers, payload = llm_service._build_request("openai", "hello", "openai:gpt-4o-mini")

    assert url.endswith("/v1/chat/completions")
    assert headers["Authorization"] == "Bearer test-openai-key"
    assert payload["model"] == "gpt-4o-mini"
    assert payload["messages"][0]["content"] == "hello"


def test_build_azure_request_adds_api_version(monkeypatch) -> None:
    # Azure OpenAI는 배포별 URL과 api-version 쿼리 파라미터를 사용합니다.
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
    # Ollama 응답의 assistant 텍스트는 message.content 아래에 들어 있습니다.
    content = llm_service._extract_content("ollama", {"message": {"content": "ollama reply"}})

    assert content == "ollama reply"


def test_call_upstream_llm_uses_ollama_prefixed_model(monkeypatch) -> None:
    # provider 접두사가 붙은 모델명은 올바른 Ollama 요청 본문으로 변환되어야 합니다.
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
    # provider 접두사가 붙은 모델명은 OpenAI 호환 upstream에서도 동작해야 합니다.
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


def test_build_openai_stream_request_sets_stream_flag(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    _url, _headers, payload = llm_service._build_request(
        "openai",
        "hello",
        "openai:gpt-4o-mini",
        stream=True,
    )

    assert payload["stream"] is True


def test_extract_openai_stream_delta() -> None:
    line = 'data: {"choices":[{"delta":{"content":"hello"}}]}'

    assert llm_service._extract_openai_stream_delta(line) == "hello"
    assert llm_service._extract_openai_stream_delta("data: [DONE]") is None


def test_extract_ollama_stream_delta() -> None:
    line = '{"message":{"content":"hello"}}'

    assert llm_service._extract_ollama_stream_delta(line) == "hello"
