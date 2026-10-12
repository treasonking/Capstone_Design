from __future__ import annotations

import os
import time
from typing import Any

from .base import LLMProvider, ProviderRequest, ProviderResponse
from .errors import (
    ProviderError,
    ProviderAuthError,
    ProviderInvalidResponseError,
    ProviderRateLimitedError,
    ProviderTimeoutError,
    ProviderUpstreamError,
)


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        configured_model: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")
        self.configured_model = (
            configured_model if configured_model is not None else os.getenv("OPENAI_MODEL", "")
        ).strip()
        self._client = client

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        model = self.configured_model or request.model
        if not self.api_key:
            raise ProviderAuthError(
                provider=self.name,
                model=model or None,
                upstream_called=False,
            )
        if not model:
            raise ProviderUpstreamError(
                provider=self.name,
                model=None,
                upstream_called=False,
            )

        client = self._client or self._create_client(request.timeout_seconds)
        started = time.perf_counter()
        request_options: dict[str, Any] = {
            "model": model,
            "input": request.safe_input,
            "store": False,
            "max_output_tokens": request.max_output_tokens,
            "timeout": request.timeout_seconds,
        }
        if request.system_instructions:
            request_options["instructions"] = request.system_instructions

        try:
            response = await client.responses.create(**request_options)
        except Exception as exc:
            raise _translate_openai_error(
                exc,
                model=model,
                latency_ms=_elapsed_ms(started),
            ) from exc

        text = getattr(response, "output_text", None)
        if not isinstance(text, str) or not text:
            raise ProviderInvalidResponseError(
                provider=self.name,
                model=model,
                upstream_called=True,
                latency_ms=_elapsed_ms(started),
            )

        response_model = getattr(response, "model", None)
        usage = _read_usage(getattr(response, "usage", None))
        finish_reason = _finish_reason(response)
        return ProviderResponse(
            text=text,
            provider=self.name,
            model=response_model if isinstance(response_model, str) and response_model else model,
            latency_ms=_elapsed_ms(started),
            finish_reason=finish_reason,
            token_usage=usage,
            external_response_id=_optional_string(getattr(response, "id", None)),
        )

    def _create_client(self, timeout_seconds: float) -> Any:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:  # pragma: no cover - packaging regression guard.
            raise ProviderUpstreamError(
                provider=self.name,
                model=self.configured_model or None,
                upstream_called=False,
            ) from exc
        self._client = AsyncOpenAI(
            api_key=self.api_key,
            timeout=timeout_seconds,
            max_retries=0,
        )
        return self._client


def _translate_openai_error(
    exc: Exception,
    *,
    model: str,
    latency_ms: float,
) -> ProviderError:
    error_name = type(exc).__name__
    common = {
        "provider": "openai",
        "model": model,
        "upstream_called": True,
        "latency_ms": latency_ms,
    }
    if error_name == "AuthenticationError":
        return ProviderAuthError(**common)
    if error_name == "RateLimitError":
        return ProviderRateLimitedError(**common)
    if error_name == "APITimeoutError":
        return ProviderTimeoutError(**common)
    return ProviderUpstreamError(**common)


def _read_usage(usage: Any) -> dict[str, int]:
    if usage is None:
        return {}
    result: dict[str, int] = {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        value = getattr(usage, key, None)
        if isinstance(value, int):
            result[key] = value
    return result


def _finish_reason(response: Any) -> str | None:
    incomplete_details = getattr(response, "incomplete_details", None)
    incomplete_reason = getattr(incomplete_details, "reason", None)
    if isinstance(incomplete_reason, str) and incomplete_reason:
        return incomplete_reason
    return _optional_string(getattr(response, "status", None))


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)
