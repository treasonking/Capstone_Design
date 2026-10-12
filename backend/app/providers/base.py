from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    request_id: str
    safe_input: str = field(repr=False)
    system_instructions: str = field(repr=False)
    model: str
    max_output_tokens: int
    timeout_seconds: float


@dataclass(frozen=True, slots=True)
class ProviderResponse:
    text: str = field(repr=False)
    provider: str
    model: str
    latency_ms: float
    finish_reason: str | None = None
    token_usage: dict[str, int] = field(default_factory=dict)
    external_response_id: str | None = None

    def audit_metadata(self) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "provider": self.provider,
            "model": self.model,
            "upstream_called": True,
            "upstream_status": "success",
            "upstream_latency_ms": self.latency_ms,
        }
        if self.finish_reason:
            metadata["upstream_finish_reason"] = self.finish_reason
        if self.token_usage:
            metadata["upstream_token_usage"] = dict(self.token_usage)
        return metadata


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Generate one fully buffered response from policy-processed input."""
