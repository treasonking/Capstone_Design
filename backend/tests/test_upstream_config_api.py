from __future__ import annotations

import asyncio

from backend.app.api.proxy import admin_upstream_config
from backend.app.services import llm_service


def test_upstream_config_reports_provider_defaults(monkeypatch) -> None:
    monkeypatch.setattr(llm_service, "DEFAULT_PROVIDER", "ollama")
    monkeypatch.setattr(llm_service, "DEFAULT_TIMEOUT_SECONDS", 15.0)
    monkeypatch.setattr(llm_service, "DEFAULT_RETRY_COUNT", 2)
    monkeypatch.setattr(llm_service, "DEFAULT_OLLAMA_MODEL", "llama3.1")
    monkeypatch.setattr(
        llm_service,
        "_PROVIDER_URLS",
        {
            **llm_service._PROVIDER_URLS,
            "ollama": "http://localhost:11434/api/chat",
        },
    )

    result = asyncio.run(admin_upstream_config())

    assert result.default_provider == "ollama"
    assert result.default_timeout_seconds == 15.0
    assert result.default_retry_count == 2
    assert result.providers["ollama"].enabled is True
    assert result.providers["ollama"].default_model == "llama3.1"


def test_upstream_config_hides_api_keys_and_marks_openai_enabled(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "super-secret-key")
    monkeypatch.setattr(llm_service, "DEFAULT_OPENAI_MODEL", "gpt-4o-mini")

    result = asyncio.run(admin_upstream_config())

    assert result.providers["openai"].enabled is True
    assert result.providers["openai"].default_model == "gpt-4o-mini"
    assert "secret" not in str(result.model_dump())
