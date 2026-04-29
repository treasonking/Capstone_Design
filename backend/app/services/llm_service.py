from __future__ import annotations

import os
from typing import Any

import httpx


DEFAULT_PROVIDER = os.getenv("UPSTREAM_LLM_PROVIDER", "mock").lower()
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "10"))
DEFAULT_RETRY_COUNT = int(os.getenv("UPSTREAM_RETRY_COUNT", "1"))

_PROVIDER_URLS = {
    "mock": os.getenv("MOCK_LLM_URL", "http://localhost:8001/v1/chat/completions"),
    "openai": os.getenv("OPENAI_CHAT_URL", "https://api.openai.com/v1/chat/completions"),
    "azure": os.getenv("AZURE_OPENAI_CHAT_URL", ""),
    "ollama": os.getenv("OLLAMA_CHAT_URL", "http://localhost:11434/api/chat"),
}


class UpstreamTimeoutError(Exception):
    pass


class UpstreamRequestError(Exception):
    pass


def _resolve_provider(model: str) -> str:
    model_lower = model.lower()
    if model_lower in _PROVIDER_URLS:
        return model_lower
    return DEFAULT_PROVIDER


def _build_request(provider: str, message: str, model: str) -> tuple[str, dict[str, str], dict[str, Any]]:
    url = _PROVIDER_URLS.get(provider) or _PROVIDER_URLS["mock"]
    headers: dict[str, str] = {}

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {"model": model, "messages": [{"role": "user", "content": message}]}
        return url, headers, payload

    if provider == "azure":
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        if api_key:
            headers["api-key"] = api_key
        payload = {"messages": [{"role": "user", "content": message}]}
        return url or _PROVIDER_URLS["mock"], headers, payload

    if provider == "ollama":
        payload = {"model": model, "messages": [{"role": "user", "content": message}], "stream": False}
        return url, headers, payload

    payload = {"messages": [{"role": "user", "content": message}]}
    return url, headers, payload


def _extract_content(provider: str, payload: dict[str, Any]) -> str:
    if provider == "ollama":
        message = payload.get("message", {})
        content = message.get("content")
    else:
        content = payload["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise UpstreamRequestError("Upstream response content is not a string.")
    return content


async def call_upstream_llm(
    message: str,
    model: str = "mock",
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    retry_count: int = DEFAULT_RETRY_COUNT,
) -> str:
    provider = _resolve_provider(model)
    url, headers, payload = _build_request(provider, message, model)
    attempts = max(retry_count, 0) + 1

    last_timeout: httpx.TimeoutException | None = None
    last_error: Exception | None = None

    for _attempt in range(attempts):
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return _extract_content(provider, response.json())
        except httpx.TimeoutException as exc:
            last_timeout = exc
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            last_error = exc

    if last_timeout is not None:
        raise UpstreamTimeoutError from last_timeout
    raise UpstreamRequestError from last_error
