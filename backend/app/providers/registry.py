from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import httpx

from .base import LLMProvider
from .errors import ProviderNotSupportedError
from .mock_provider import MockProvider
from .openai_provider import OpenAIProvider


DEFAULT_MOCK_ENDPOINT = "http://localhost:8001/v1/chat/completions"
ALLOWED_PROVIDER_NAMES = frozenset({"mock", "openai"})


class ProviderRegistry:
    """Fixed provider allowlist; request data cannot supply endpoints or factories."""

    def __init__(
        self,
        *,
        mock_client_factory: Callable[..., Any] = httpx.AsyncClient,
        openai_client: Any | None = None,
    ) -> None:
        self._mock_client_factory = mock_client_factory
        self._openai_client = openai_client

    def get(self, provider_name: str) -> LLMProvider:
        normalized = provider_name.strip().lower()
        if normalized == "mock":
            return MockProvider(
                endpoint=os.getenv("MOCK_LLM_URL", DEFAULT_MOCK_ENDPOINT),
                client_factory=self._mock_client_factory,
            )
        if normalized == "openai":
            return OpenAIProvider(client=self._openai_client)
        raise ProviderNotSupportedError(
            provider=normalized or "unknown",
            model=None,
            upstream_called=False,
        )
