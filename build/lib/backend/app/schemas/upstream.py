from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UpstreamProviderConfig(BaseModel):
    # 관리자에게 보여줄 LLM 제공자별 실행 설정입니다.
    enabled: bool
    url: str
    default_model: str
    api_version: str | None = None


class UpstreamConfigResponse(BaseModel):
    # 현재 upstream 설정 확인 API의 응답 형식입니다.
    default_provider: str
    default_timeout_seconds: float
    default_retry_count: int
    providers: dict[str, UpstreamProviderConfig] = Field(default_factory=dict)
