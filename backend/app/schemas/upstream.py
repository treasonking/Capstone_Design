from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UpstreamProviderConfig(BaseModel):
    enabled: bool
    url: str
    default_model: str
    api_version: str | None = None


class UpstreamConfigResponse(BaseModel):
    default_provider: str
    default_timeout_seconds: float
    default_retry_count: int
    providers: dict[str, UpstreamProviderConfig] = Field(default_factory=dict)
