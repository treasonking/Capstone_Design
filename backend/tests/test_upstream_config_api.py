from __future__ import annotations

import asyncio

from backend.app.api.proxy import admin_upstream_config


def test_upstream_config_reports_mock_defaults(monkeypatch) -> None:
    # 관리자 설정 API는 현재 실행 기본값을 반영해야 합니다.
    monkeypatch.setenv("ADMIN_API_TOKEN", "test-admin-token")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("UPSTREAM_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("UPSTREAM_TIMEOUT_SECONDS", raising=False)

    result = asyncio.run(admin_upstream_config("test-admin-token"))

    assert result.default_provider == "mock"
    assert result.default_timeout_seconds == 10.0
    assert result.default_retry_count == 0
    assert result.automatic_fallback is False
    assert result.allowed_providers == ["mock", "openai"]
    assert result.providers["mock"].enabled is True
    assert "azure" not in result.providers
    assert "ollama" not in result.providers


def test_upstream_config_hides_api_keys_and_marks_openai_enabled(monkeypatch) -> None:
    # OpenAI 사용 가능 여부는 보여주되, API 키 자체는 절대 노출하면 안 됩니다.
    monkeypatch.setenv("ADMIN_API_TOKEN", "test-admin-token")
    monkeypatch.setenv("OPENAI_API_KEY", "super-secret-key")
    monkeypatch.setenv("OPENAI_MODEL", "configured-test-model")

    result = asyncio.run(admin_upstream_config("test-admin-token"))

    assert result.providers["openai"].enabled is True
    assert result.providers["openai"].default_model == "configured-test-model"
    assert result.providers["openai"].url.endswith("/v1/responses")
    assert "secret" not in str(result.model_dump())
