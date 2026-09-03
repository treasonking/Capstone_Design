from __future__ import annotations

import asyncio
import os

import pytest

from backend.app.providers.base import ProviderRequest
from backend.app.providers.openai_provider import OpenAIProvider


_LIVE_ENABLED = os.getenv("RUN_LIVE_OPENAI_TESTS") == "1"
_HAS_REQUIRED_CONFIG = bool(os.getenv("OPENAI_API_KEY")) and bool(os.getenv("OPENAI_MODEL"))


@pytest.mark.skipif(
    not (_LIVE_ENABLED and _HAS_REQUIRED_CONFIG),
    reason="requires RUN_LIVE_OPENAI_TESTS=1, OPENAI_API_KEY, and OPENAI_MODEL",
)
def test_live_openai_safe_request() -> None:
    request = ProviderRequest(
        request_id="live-openai-safe-smoke",
        safe_input="Reply with the single word OK.",
        system_instructions="Return a concise, harmless response.",
        model=os.environ["OPENAI_MODEL"],
        max_output_tokens=16,
        timeout_seconds=30,
    )

    response = asyncio.run(OpenAIProvider().generate(request))

    assert response.provider == "openai"
    assert response.text.strip()
    assert response.latency_ms >= 0
