from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

DEFAULT_OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MOCK_CHAT_URL = "http://localhost:8001/v1/chat/completions"
DEFAULT_OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
DEFAULT_PROVIDER = "mock"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_RETRY_COUNT = 1
DEFAULT_AZURE_API_VERSION = "2024-02-15-preview"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OLLAMA_MODEL = "llama3"
DEFAULT_AZURE_DEPLOYMENT = ""
_PROVIDER_URLS = {
    "mock": DEFAULT_MOCK_CHAT_URL,
    "openai": DEFAULT_OPENAI_CHAT_URL,
    "azure": "",
    "ollama": DEFAULT_OLLAMA_CHAT_URL,
}


class UpstreamTimeoutError(Exception):
    def __init__(self, attempts: int) -> None:
        super().__init__("Upstream request timed out.")
        self.attempts = attempts


class UpstreamRequestError(Exception):
    def __init__(
        self,
        message: str = "Upstream request failed.",
        *,
        attempts: int,
        status_code: int | None = None,
        reason_code: str = "UPSTREAM_ERROR",
    ) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.status_code = status_code
        self.reason_code = reason_code


def _default_provider() -> str:
    return os.getenv("UPSTREAM_LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower() or DEFAULT_PROVIDER


def _default_timeout_seconds() -> float:
    return float(os.getenv("UPSTREAM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))


def _default_retry_count() -> int:
    return int(os.getenv("UPSTREAM_RETRY_COUNT", str(DEFAULT_RETRY_COUNT)))


def _default_azure_api_version() -> str:
    return os.getenv("AZURE_OPENAI_API_VERSION", DEFAULT_AZURE_API_VERSION)


def _default_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)


def _default_ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)


def _default_azure_deployment() -> str:
    return os.getenv("AZURE_OPENAI_DEPLOYMENT", DEFAULT_AZURE_DEPLOYMENT)


def _provider_urls() -> dict[str, str]:
    return {
        "mock": os.getenv("MOCK_LLM_URL", _PROVIDER_URLS["mock"]),
        "openai": os.getenv("OPENAI_CHAT_URL", _PROVIDER_URLS["openai"]),
        "azure": os.getenv("AZURE_OPENAI_CHAT_URL", _PROVIDER_URLS["azure"]),
        "ollama": os.getenv("OLLAMA_CHAT_URL", _PROVIDER_URLS["ollama"]),
    }


def get_upstream_config_summary() -> dict[str, Any]:
    # 관리자가 현재 실행 설정을 확인할 수 있게 하되, API 키 같은 비밀값은 노출하지 않습니다.
    provider_urls = _provider_urls()
    return {
        "default_provider": _default_provider(),
        "default_timeout_seconds": _default_timeout_seconds(),
        "default_retry_count": _default_retry_count(),
        "providers": {
            "mock": {
                "enabled": True,
                "url": provider_urls["mock"],
                "default_model": "mock",
            },
            "openai": {
                "enabled": bool(os.getenv("OPENAI_API_KEY", "")),
                "url": provider_urls["openai"],
                "default_model": _default_openai_model(),
            },
            "azure": {
                "enabled": bool(os.getenv("AZURE_OPENAI_API_KEY", "")) and bool(provider_urls["azure"]),
                "url": provider_urls["azure"],
                "default_model": _default_azure_deployment() or _default_openai_model(),
                "api_version": _default_azure_api_version(),
            },
            "ollama": {
                "enabled": bool(provider_urls["ollama"]),
                "url": provider_urls["ollama"],
                "default_model": _default_ollama_model(),
            },
        },
    }


def _split_model_target(model: str) -> tuple[str, str]:
    # "ollama:llama3" 같은 provider:model 형식과 "mock" 같은 기존 형식을 모두 지원합니다.
    provider_urls = _provider_urls()
    raw_model = (model or "").strip()
    if ":" in raw_model:
        provider_prefix, provider_model = raw_model.split(":", 1)
        provider = provider_prefix.lower().strip()
        if provider in provider_urls:
            return provider, provider_model.strip()

    provider = _resolve_provider(raw_model)
    if provider == "openai":
        return provider, _default_openai_model()
    if provider == "azure":
        return provider, _default_azure_deployment() or _default_openai_model()
    if provider == "ollama":
        return provider, _default_ollama_model()
    return provider, raw_model or "mock"


def _resolve_provider(model: str) -> str:
    provider_urls = _provider_urls()
    model_lower = model.lower()
    if model_lower in provider_urls:
        return model_lower
    return _default_provider()


def _with_query_param(url: str, key: str, value: str) -> str:
    # Azure OpenAI는 api-version 값을 쿼리 문자열로 요구합니다.
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


def _build_request(provider: str, message: str, model: str, *, stream: bool = False) -> tuple[str, dict[str, str], dict[str, Any]]:
    provider_urls = _provider_urls()
    url = provider_urls.get(provider) or provider_urls["mock"]
    headers: dict[str, str] = {"Content-Type": "application/json"}
    _provider, upstream_model = _split_model_target(model)

    # 각 LLM 제공자는 요청 본문과 인증 헤더 형식이 조금씩 다릅니다.
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise UpstreamRequestError(
                "OPENAI_API_KEY must be set when UPSTREAM_LLM_PROVIDER=openai.",
                attempts=0,
                reason_code="UPSTREAM_CONFIG_ERROR",
            )
        headers["Authorization"] = f"Bearer {api_key}"
        payload = {"model": upstream_model, "messages": [{"role": "user", "content": message}]}
        if stream:
            payload["stream"] = True
        return url, headers, payload

    if provider == "azure":
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        azure_url = provider_urls["azure"]
        missing_fields = [
            name
            for name, value in (
                ("AZURE_OPENAI_API_KEY", api_key),
                ("AZURE_OPENAI_CHAT_URL", azure_url),
            )
            if not value
        ]
        if missing_fields:
            raise UpstreamRequestError(
                f"Missing Azure OpenAI configuration: {', '.join(missing_fields)}",
                attempts=0,
                reason_code="UPSTREAM_CONFIG_ERROR",
            )
        headers["api-key"] = api_key
        payload = {"messages": [{"role": "user", "content": message}]}
        if stream:
            payload["stream"] = True
        azure_url = _with_query_param(azure_url, "api-version", _default_azure_api_version())
        return azure_url, headers, payload

    if provider == "ollama":
        payload = {"model": upstream_model, "messages": [{"role": "user", "content": message}], "stream": stream}
        return url, headers, payload

    payload = {"messages": [{"role": "user", "content": message}]}
    return url, headers, payload


def _extract_content(provider: str, payload: dict[str, Any]) -> str:
    # Ollama와 OpenAI 호환 API는 응답 본문에서 텍스트가 들어 있는 위치가 다릅니다.
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
    timeout_seconds: float | None = None,
    retry_count: int | None = None,
) -> str:
    timeout_seconds = _default_timeout_seconds() if timeout_seconds is None else timeout_seconds
    retry_count = _default_retry_count() if retry_count is None else retry_count
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
            # 429나 5xx처럼 일시적일 가능성이 있는 HTTP 오류만 재시도합니다.
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


def _extract_openai_stream_delta(raw_line: str) -> str | None:
    if not raw_line.startswith("data:"):
        return None

    data = raw_line.removeprefix("data:").strip()
    if not data or data == "[DONE]":
        return None

    payload = json.loads(data)
    delta = payload.get("choices", [{}])[0].get("delta", {})
    content = delta.get("content")
    return content if isinstance(content, str) and content else None


def _extract_ollama_stream_delta(raw_line: str) -> str | None:
    if not raw_line:
        return None

    payload = json.loads(raw_line)
    message = payload.get("message", {})
    content = message.get("content")
    return content if isinstance(content, str) and content else None


async def stream_upstream_llm(
    message: str,
    model: str = "mock",
    timeout_seconds: float | None = None,
) -> AsyncIterator[str]:
    timeout_seconds = _default_timeout_seconds() if timeout_seconds is None else timeout_seconds
    provider, _upstream_model = _split_model_target(model)

    if provider == "mock":
        content = await call_upstream_llm(message, model=model, timeout_seconds=timeout_seconds, retry_count=0)
        yield content
        return

    url, headers, payload = _build_request(provider, message, model, stream=True)

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for raw_line in response.aiter_lines():
                    if provider == "ollama":
                        chunk = _extract_ollama_stream_delta(raw_line)
                    else:
                        chunk = _extract_openai_stream_delta(raw_line)
                    if chunk:
                        yield chunk
    except httpx.TimeoutException as exc:
        raise UpstreamTimeoutError(attempts=1) from exc
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        status_code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
        raise UpstreamRequestError("Upstream stream failed.", attempts=1, status_code=status_code) from exc
