from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProxyRequest(BaseModel):
    # Client request sent to the security proxy instead of directly to an LLM.
    message: str
    policy_id: str = "default"
    user_id: str = "anonymous"
    model: str = "mock"


class ProxyResponse(BaseModel):
    # Standardized proxy response that includes both LLM output and policy result.
    request_id: str
    action: str
    reason_code: str | None
    reasons: list[str] = Field(default_factory=list)
    input_action: str
    output_action: str | None = None
    content: str | None
    audit_summary: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    # Minimal OpenAI-style request schema used by the local mock endpoint.
    model: str = "mock"
    messages: list[ChatMessage]
