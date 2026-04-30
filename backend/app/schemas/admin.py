from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AdminStatsResponse(BaseModel):
    # Summary cards for the admin dashboard.
    total_requests: int
    blocked_requests: int
    masked_requests: int
    warned_requests: int
    allowed_requests: int
    error_requests: int
    detection_type_counts: dict[str, int] = Field(default_factory=dict)


class RecentBlockItem(BaseModel):
    # Row model for the recent blocked-history table.
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


class ReasonCodeStatItem(BaseModel):
    # Frequency item for charts or ranked reason-code lists.
    reason_code: str
    count: int
