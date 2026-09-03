from __future__ import annotations


class ProviderError(Exception):
    code = "PROVIDER_UPSTREAM_ERROR"
    upstream_status = "upstream_error"

    def __init__(
        self,
        *,
        provider: str,
        model: str | None = None,
        upstream_called: bool,
        latency_ms: float | None = None,
    ) -> None:
        super().__init__(self.code)
        self.provider = provider
        self.model = model
        self.upstream_called = upstream_called
        self.latency_ms = latency_ms

    def audit_metadata(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "model": self.model,
            "upstream_called": self.upstream_called,
            "upstream_status": self.upstream_status,
            "upstream_latency_ms": self.latency_ms,
            "error_type": self.code,
        }


class ProviderNotSupportedError(ProviderError):
    code = "PROVIDER_NOT_SUPPORTED"
    upstream_status = "not_supported"


class ProviderAuthError(ProviderError):
    code = "PROVIDER_AUTH_ERROR"
    upstream_status = "auth_error"


class ProviderRateLimitedError(ProviderError):
    code = "PROVIDER_RATE_LIMITED"
    upstream_status = "rate_limited"


class ProviderTimeoutError(ProviderError):
    code = "PROVIDER_TIMEOUT"
    upstream_status = "timeout"


class ProviderUpstreamError(ProviderError):
    code = "PROVIDER_UPSTREAM_ERROR"
    upstream_status = "upstream_error"


class ProviderInvalidResponseError(ProviderError):
    code = "PROVIDER_INVALID_RESPONSE"
    upstream_status = "invalid_response"
