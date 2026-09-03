from __future__ import annotations

import asyncio

from backend.app.providers.base import LLMProvider, ProviderRequest, ProviderResponse
from backend.app.providers.registry import ProviderRegistry
from backend.app.services import llm_service


class _CaptureProvider(LLMProvider):
    name = "mock"

    def __init__(self) -> None:
        self.request: ProviderRequest | None = None

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        self.request = request
        return ProviderResponse(
            text="provider response",
            provider=self.name,
            model=request.model,
            latency_ms=1.25,
            finish_reason="stop",
        )


class _CaptureRegistry(ProviderRegistry):
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self.selected_name: str | None = None

    def get(self, provider_name: str) -> LLMProvider:
        self.selected_name = provider_name
        return self.provider


def test_generate_uses_environment_provider_and_preserves_request_id(monkeypatch) -> None:
    provider = _CaptureProvider()
    registry = _CaptureRegistry(provider)
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    response = asyncio.run(
        llm_service.generate_upstream_response(
            "policy-safe input",
            request_id="request-123",
            requested_model="openai:attacker-selected-model",
            registry=registry,
        )
    )

    assert response.text == "provider response"
    assert registry.selected_name == "mock"
    assert provider.request is not None
    assert provider.request.request_id == "request-123"
    assert provider.request.safe_input == "policy-safe input"
    assert provider.request.model == "mock"


def test_request_model_cannot_switch_provider_or_openai_model(monkeypatch) -> None:
    provider = _CaptureProvider()
    provider.name = "openai"
    registry = _CaptureRegistry(provider)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_MODEL", "administrator-configured-model")

    asyncio.run(
        llm_service.generate_upstream_response(
            "safe input",
            request_id="request-model-lock",
            requested_model="mock:http://attacker.invalid",
            registry=registry,
        )
    )

    assert registry.selected_name == "openai"
    assert provider.request is not None
    assert provider.request.model == "administrator-configured-model"


def test_openai_settings_use_bounded_defaults(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("OPENAI_MAX_OUTPUT_TOKENS", raising=False)

    assert llm_service.configured_timeout_seconds() == 30.0
    assert llm_service.configured_max_output_tokens() == 1000


def test_legacy_provider_environment_is_read_only_when_new_name_absent(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("UPSTREAM_LLM_PROVIDER", "openai")

    assert llm_service.configured_provider_name() == "openai"


def test_compatibility_text_facade_returns_only_text(monkeypatch) -> None:
    async def _fake_generate(*args, **kwargs) -> ProviderResponse:
        return ProviderResponse(
            text="compatibility response",
            provider="mock",
            model="mock",
            latency_ms=0.5,
        )

    monkeypatch.setattr(llm_service, "generate_upstream_response", _fake_generate)

    content = asyncio.run(llm_service.call_upstream_llm("safe input"))

    assert content == "compatibility response"
