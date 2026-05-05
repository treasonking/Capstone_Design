from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AdminStatsResponse(BaseModel):
    # 관리자 대시보드의 요약 카드에 표시할 통계 응답입니다.
    total_requests: int
    blocked_requests: int
    masked_requests: int
    warned_requests: int
    allowed_requests: int
    error_requests: int
    detection_type_counts: dict[str, int] = Field(default_factory=dict)
    average_latency_ms: float = 0.0
    today_blocked_requests: int = 0
    today_masked_requests: int = 0
    today_warned_requests: int = 0


class RecentBlockItem(BaseModel):
    # 최근 차단 이력 테이블의 한 행을 표현하는 응답 형식입니다.
    request_id: str
    user_id: str
    timestamp: str | None = None
    action: str
    reason_codes: list[str] = Field(default_factory=list)
    pii_detected: bool = False
    injection_detected: bool = False
    latency_ms: float | int | None = None
    upstream_call: bool = False
    input_action: str | None = None
    output_action: str | None = None
    detector_counts: dict[str, int] = Field(default_factory=dict)
    masked_preview: str | None = None
    policy_version: str | None = None
    model_version: str | None = None


class ReasonCodeStatItem(BaseModel):
    # 차트나 순위 목록에 사용할 reason_code 빈도 항목입니다.
    reason_code: str
    count: int


class PolicyRuleView(BaseModel):
    reason_code: str
    action: str
    priority: int
    threshold: float
    description: str = ""
    enabled: bool = True


class PolicyConfigResponse(BaseModel):
    policy_id: str
    default_action: str
    policy_version: str | None = None
    model_version: str | None = None
    rules: list[PolicyRuleView] = Field(default_factory=list)


class AuditLogItem(BaseModel):
    request_id: str
    user_id: str
    timestamp: str | None = None
    action: str
    reason_codes: list[str] = Field(default_factory=list)
    reason_code: str | None = None
    pii_detected: bool = False
    injection_detected: bool = False
    model_detected: bool = False
    latency_ms: float | int | None = None
    detector_counts: dict[str, int] = Field(default_factory=dict)
    policy_version: str | None = None
    model_version: str | None = None
    masked_preview: str | None = None
