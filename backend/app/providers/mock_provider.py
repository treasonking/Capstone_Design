from __future__ import annotations

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


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(
        self,
        *,
        endpoint: str,
        client_factory: Callable[..., Any] = httpx.AsyncClient,
    ) -> None:
        self.endpoint = endpoint
        self._client_factory = client_factory

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        started = time.perf_counter()
        payload = {
            "model": request.model or "mock",
            "messages": [{"role": "user", "content": request.safe_input}],
        }
        try:
            async with self._client_factory(timeout=request.timeout_seconds) as client:
                response = await client.post(
                    self.endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
            response.raise_for_status()
            response_payload = response.json()
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                provider=self.name,
                model=request.model,
                upstream_called=True,
                latency_ms=_elapsed_ms(started),
            ) from exc
        except httpx.HTTPStatusError as exc:
            error_type: type[ProviderUpstreamError] | type[ProviderAuthError] | type[ProviderRateLimitedError]
            if exc.response.status_code == 401:
                error_type = ProviderAuthError
            elif exc.response.status_code == 429:
                error_type = ProviderRateLimitedError
            else:
                error_type = ProviderUpstreamError
            raise error_type(
                provider=self.name,
                model=request.model,
                upstream_called=True,
                latency_ms=_elapsed_ms(started),
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderUpstreamError(
                provider=self.name,
                model=request.model,
                upstream_called=True,
                latency_ms=_elapsed_ms(started),
            ) from exc
        except (TypeError, ValueError) as exc:
            raise ProviderInvalidResponseError(
                provider=self.name,
                model=request.model,
                upstream_called=True,
                latency_ms=_elapsed_ms(started),
            ) from exc

        try:
            choice = response_payload["choices"][0]
            text = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderInvalidResponseError(
                provider=self.name,
                model=request.model,
                upstream_called=True,
                latency_ms=_elapsed_ms(started),
            ) from exc
        if not isinstance(text, str) or not text:
            raise ProviderInvalidResponseError(
                provider=self.name,
                model=request.model,
                upstream_called=True,
                latency_ms=_elapsed_ms(started),
            )

        usage = _token_usage(response_payload.get("usage"))
        return ProviderResponse(
            text=text,
            provider=self.name,
            model=str(response_payload.get("model") or request.model or "mock"),
            latency_ms=_elapsed_ms(started),
            finish_reason=choice.get("finish_reason") if isinstance(choice, dict) else None,
            token_usage=usage,
            external_response_id=_optional_string(response_payload.get("id")),
        )


def _token_usage(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        token_count = value.get(key)
        if isinstance(token_count, int):
            result[key] = token_count
    return result


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)
