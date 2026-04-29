from __future__ import annotations

import os
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx


DEFAULT_PROVIDER = os.getenv("UPSTREAM_LLM_PROVIDER", "mock").lower()
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", "10"))
DEFAULT_RETRY_COUNT = int(os.getenv("UPSTREAM_RETRY_COUNT", "1"))
DEFAULT_AZURE_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
DEFAULT_AZURE_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")

_PROVIDER_URLS = {
    "mock": os.getenv("MOCK_LLM_URL", "http://localhost:8001/v1/chat/completions"),
    "openai": os.getenv("OPENAI_CHAT_URL", "https://api.openai.com/v1/chat/completions"),
    "azure": os.getenv("AZURE_OPENAI_CHAT_URL", ""),
    "ollama": os.getenv("OLLAMA_CHAT_URL", "http://localhost:11434/api/chat"),
}


class UpstreamTimeoutError(Exception):
    def __init__(self, attempts: int) -> None:
        super().__init__("Upstream request timed out.")
        self.attempts = attempts


class UpstreamRequestError(Exception):
    def __init__(self, message: str = "Upstream request failed.", *, attempts: int, status_code: int | None = None) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.status_code = status_code


def _split_model_target(model: str) -> tuple[str, str]:
    raw_model = (model or "").strip()
    if ":" in raw_model:
        provider_prefix, provider_model = raw_model.split(":", 1)
        provider = provider_prefix.lower().strip()
        if provider in _PROVIDER_URLS:
            return provider, provider_model.strip()

    provider = _resolve_provider(raw_model)
    if provider == "openai":
        return provider, DEFAULT_OPENAI_MODEL
    if provider == "azure":
        return provider, DEFAULT_AZURE_DEPLOYMENT or DEFAULT_OPENAI_MODEL
    if provider == "ollama":
        return provider, DEFAULT_OLLAMA_MODEL
    return provider, raw_model or "mock"


def _resolve_provider(model: str) -> str:
    model_lower = model.lower()
    if model_lower in _PROVIDER_URLS:
        return model_lower
    return DEFAULT_PROVIDER


def _with_query_param(url: str, key: str, value: str) -> str:
    split_result = urlsplit(url)
    query = dict(parse_qsl(split_result.query, keep_blank_values=True))
    query.setdefault(key, value)
    return urlunsplit(
        (
            split_result.scheme,
            split_result.netloc,
            split_result.path,
            urlencode(query),
            split_result.fragment,
        )
    )


def _build_request(provider: str, message: str, model: str) -> tuple[str, dict[str, str], dict[str, Any]]:
    url = _PROVIDER_URLS.get(provider) or _PROVIDER_URLS["mock"]
    headers: dict[str, str] = {"Content-Type": "application/json"}
    _provider, upstream_model = _split_model_target(model)

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        payload = {"model": upstream_model, "messages": [{"role": "user", "content": message}]}
        return url, headers, payload

    if provider == "azure":
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        if api_key:
            headers["api-key"] = api_key
        payload = {"messages": [{"role": "user", "content": message}]}
        azure_url = _with_query_param(url or _PROVIDER_URLS["mock"], "api-version", DEFAULT_AZURE_API_VERSION)
        return azure_url, headers, payload

    if provider == "ollama":
        payload = {"model": upstream_model, "messages": [{"role": "user", "content": message}], "stream": False}
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
        raise UpstreamRequestError("Upstream response content is not a string.", attempts=1)
    return content


def _is_retryable_http_error(exc: httpx.HTTPError) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code == 429 or status_code >= 500
    return False


async def call_upstream_llm(
    message: str,
    model: str = "mock",
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    retry_count: int = DEFAULT_RETRY_COUNT,
) -> str:
    provider, _upstream_model = _split_model_target(model)
    url, headers, payload = _build_request(provider, message, model)
    attempts = max(retry_count, 0) + 1

    last_timeout: httpx.TimeoutException | None = None
    last_error: Exception | None = None
    last_status_code: int | None = None

    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return _extract_content(provider, response.json())
        except httpx.TimeoutException as exc:
            last_timeout = exc
            if attempt == attempts:
                raise UpstreamTimeoutError(attempts=attempt) from exc
        except httpx.HTTPStatusError as exc:
            last_error = exc
            last_status_code = exc.response.status_code
            if not _is_retryable_http_error(exc) or attempt == attempts:
                raise UpstreamRequestError(
                    "Upstream HTTP request failed.",
                    attempts=attempt,
                    status_code=last_status_code,
                ) from exc
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            last_error = exc
            raise UpstreamRequestError(
                "Upstream request failed.",
                attempts=attempt,
                status_code=last_status_code,
            ) from exc

    if last_timeout is not None:
        raise UpstreamTimeoutError(attempts=attempts) from last_timeout
    raise UpstreamRequestError(attempts=attempts, status_code=last_status_code) from last_error
