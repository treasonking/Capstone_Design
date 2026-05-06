from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProxyRequest(BaseModel):
    # 클라이언트가 LLM에 직접 보내지 않고 보안 프록시로 보내는 요청 형식입니다.
    message: str
    policy_id: str = "default"
    user_id: str = "anonymous"
    model: str = ""


class ProxyResponse(BaseModel):
    # LLM 응답과 정책 처리 결과를 함께 담는 표준 프록시 응답 형식입니다.
    request_id: str
    action: str
    reason_code: str | None
    reasons: list[str] = Field(default_factory=list)
    input_action: str
    output_action: str | None = None
    content: str | None
    audit_summary: dict[str, Any] = Field(default_factory=dict)


class DetectionPreviewItem(BaseModel):
    detector_type: str
    category: str
    reason_code: str
    detector_source: str
    confidence: float
    start: int
    end: int


class ProxyAnalyzeResponse(BaseModel):
    request_id: str
    action: str
    reason_code: str | None
    reasons: list[str] = Field(default_factory=list)
    pii_detected: bool
    injection_detected: bool
    masked_text: str | None = None
    should_call_llm: bool
    upstream_call: bool = False
    recommendation: str
    detector_results: list[DetectionPreviewItem] = Field(default_factory=list)
    audit_summary: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    # 로컬 Mock 엔드포인트에서 사용하는 최소 OpenAI 호환 요청 형식입니다.
    model: str = "mock"
    messages: list[ChatMessage]
