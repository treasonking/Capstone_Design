from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ProxyRequest(BaseModel):
    # 클라이언트가 LLM에 직접 보내지 않고 보안 프록시로 보내는 요청 형식입니다.
    message: str = Field(min_length=1, max_length=4000)
    policy_id: str = "default"
    user_id: str = "anonymous"
    model: str = ""
    assistant: Literal["general", "resident_center"] = "general"
    history: list[ConversationMessage] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def bounded_conversation(self) -> "ProxyRequest":
        if sum(len(item.content) for item in self.history) + len(self.message) > 20000:
            raise ValueError("대화 내용은 총 20,000자 이내여야 합니다.")
        if self.history and (len(self.history) % 2 or any(
            item.role != ("user" if index % 2 == 0 else "assistant")
            for index, item in enumerate(self.history)
        )):
            raise ValueError("대화 이력은 사용자·답변 쌍으로 전달해야 합니다.")
        return self


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


class UserAnalyzeResponse(BaseModel):
    """Preflight only; no provider call or output validation result."""
    action: Literal["ALLOW", "MASK", "WARN", "BLOCK"]


class UserChatResponse(BaseModel):
    """Minimal projection of the final, server-validated response."""
    action: Literal["ALLOW", "MASK", "WARN", "BLOCK", "ERROR"]
    content: str | None
    input_masked: bool = False
    output_masked: bool = False


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
