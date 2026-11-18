from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import httpx

from .base import LLMProvider, ProviderRequest, ProviderResponse
from .errors import (
    ProviderAuthError,
    ProviderInvalidResponseError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUpstreamError,
)


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


class OllamaProvider(LLMProvider):
    """Non-streaming adapter for a locally hosted Ollama chat model."""

    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str | None = None,
        configured_model: str | None = None,
        client_factory: Callable[..., Any] = httpx.AsyncClient,
    ) -> None:
        self.base_url = (
            base_url if base_url is not None else os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
        ).strip().rstrip("/")
        self.configured_model = (
            configured_model if configured_model is not None else os.getenv("OLLAMA_MODEL", "")
        ).strip()
        self._client_factory = client_factory

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        model = self.configured_model or request.model
        if not model:
            raise ProviderUpstreamError(
                provider=self.name,
                model=None,
                upstream_called=False,
            )

        messages: list[dict[str, str]] = []
        if request.system_instructions:
            messages.append({"role": "system", "content": request.system_instructions})
        messages.append({"role": "user", "content": request.safe_input})
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": request.max_output_tokens},
        }

        endpoint = f"{self.base_url or DEFAULT_OLLAMA_BASE_URL}/api/chat"
        started = time.perf_counter()
        try:
            async with self._client_factory(timeout=request.timeout_seconds) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
            response.raise_for_status()
            response_payload = response.json()
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                provider=self.name,
                model=model,
                upstream_called=True,
                latency_ms=_elapsed_ms(started),
            ) from exc
        except httpx.HTTPStatusError as exc:
            error_type: type[ProviderUpstreamError] | type[ProviderAuthError] | type[ProviderRateLimitedError]
            if exc.response.status_code in {401, 403}:
                error_type = ProviderAuthError
            elif exc.response.status_code == 429:
                error_type = ProviderRateLimitedError
            else:
                error_type = ProviderUpstreamError
            raise error_type(
                provider=self.name,
                model=model,
                upstream_called=True,
                latency_ms=_elapsed_ms(started),
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUpstreamError(
                provider=self.name,
                model=model,
                upstream_called=True,
                latency_ms=_elapsed_ms(started),
            ) from exc
        except (TypeError, ValueError) as exc:
            raise ProviderInvalidResponseError(
                provider=self.name,
                model=model,
                upstream_called=True,
                latency_ms=_elapsed_ms(started),
            ) from exc

        if not isinstance(response_payload, dict):
            raise ProviderInvalidResponseError(
                provider=self.name,
                model=model,
                upstream_called=True,
                latency_ms=_elapsed_ms(started),
            )
        try:
            message = response_payload["message"]
            if not isinstance(message, dict):
                raise TypeError("message must be an object")
            text = message["content"]
        except (KeyError, TypeError) as exc:
            raise ProviderInvalidResponseError(
                provider=self.name,
                model=model,
                upstream_called=True,
                latency_ms=_elapsed_ms(started),
            ) from exc
        if not isinstance(text, str) or not text:
            raise ProviderInvalidResponseError(
                provider=self.name,
                model=model,
                upstream_called=True,
                latency_ms=_elapsed_ms(started),
            )

        usage = _token_usage(response_payload)
        return ProviderResponse(
            text=text,
            provider=self.name,
            model=_optional_string(response_payload.get("model")) or model,
            latency_ms=_elapsed_ms(started),
            finish_reason=_optional_string(response_payload.get("done_reason")),
            token_usage=usage,
        )


def _token_usage(payload: dict[str, Any]) -> dict[str, int]:
    prompt_tokens = payload.get("prompt_eval_count")
    output_tokens = payload.get("eval_count")
    usage: dict[str, int] = {}
    if isinstance(prompt_tokens, int):
        usage["input_tokens"] = prompt_tokens
    if isinstance(output_tokens, int):
        usage["output_tokens"] = output_tokens
    if isinstance(prompt_tokens, int) and isinstance(output_tokens, int):
        usage["total_tokens"] = prompt_tokens + output_tokens
    return usage


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)
