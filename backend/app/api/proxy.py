from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse

from backend.app.detection.models import PolicyAction
from backend.app.engine.policy_engine import evaluate_policy
from backend.app.schemas.admin import AdminStatsResponse, ReasonCodeStatItem, RecentBlockItem
from backend.app.schemas.proxy import ChatCompletionRequest, ProxyRequest, ProxyResponse
from backend.app.schemas.upstream import UpstreamConfigResponse
from backend.app.services.audit_service import get_admin_stats, get_reason_code_stats, get_recent_block_history
from backend.app.services.llm_service import get_upstream_config_summary
from backend.app.services.proxy_service import (
    POLICY_PATH,
    _audit_from_detections,
    _merge_detections,
    _resolve_reason_code,
    process_proxy_chat,
    process_proxy_chat_stream,
)

# 사용자용 프록시 API와 관리자/데모용 API를 함께 제공하는 FastAPI 진입점입니다.
app = FastAPI()


def _admin_api_token() -> str:
    return os.getenv("ADMIN_API_TOKEN", "dev-admin-token")


def _require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    if x_admin_token is not None and not isinstance(x_admin_token, str):
        return
    if x_admin_token != _admin_api_token():
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post("/proxy/chat")
async def proxy_chat(req: ProxyRequest) -> ProxyResponse:
    return await process_proxy_chat(req)


@app.post("/proxy/chat/stream")
async def proxy_chat_stream(req: ProxyRequest) -> StreamingResponse:
    return StreamingResponse(process_proxy_chat_stream(req), media_type="text/event-stream")


@app.get("/admin/stats")
async def admin_stats(x_admin_token: str | None = Header(default=None)) -> AdminStatsResponse:
    _require_admin_token(x_admin_token)
    return AdminStatsResponse(**get_admin_stats())


@app.get("/admin/recent-blocks")
async def admin_recent_blocks(limit: int = 10, x_admin_token: str | None = Header(default=None)) -> list[RecentBlockItem]:
    _require_admin_token(x_admin_token)
    return [RecentBlockItem(**entry) for entry in get_recent_block_history(limit=limit)]


@app.get("/admin/reason-codes")
async def admin_reason_codes(x_admin_token: str | None = Header(default=None)) -> list[ReasonCodeStatItem]:
    _require_admin_token(x_admin_token)
    return [ReasonCodeStatItem(**entry) for entry in get_reason_code_stats()]


@app.get("/admin/upstream-config")
async def admin_upstream_config(x_admin_token: str | None = Header(default=None)) -> UpstreamConfigResponse:
    _require_admin_token(x_admin_token)
    return UpstreamConfigResponse(**get_upstream_config_summary())


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    """로컬 정책 데모용 OpenAI 호환 Mock 엔드포인트입니다."""
    started = time.perf_counter()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    request_id = str(uuid.uuid4())
    user_messages = [message.content for message in req.messages if message.role == "user"]
    message = "\n".join(user_messages)

    detections = _merge_detections(message)
    decision = evaluate_policy(message, detections, POLICY_PATH)
    action = decision.final_action.value
    audit = _audit_from_detections(action, decision.reasons, detections)
    # 실제 모델 없이도 데모할 수 있도록 메인 프록시와 같은 정책 흐름을 따릅니다.
    content = None if action == PolicyAction.BLOCK.value else decision.masked_text or "mock response"

    return {
        "id": request_id,
        "object": "chat.completion",
        "model": req.model,
        "action": action,
        "reason_code": _resolve_reason_code(decision.reasons),
        "reasons": decision.reasons,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "content_filter" if action == PolicyAction.BLOCK.value else "stop",
            }
        ],
        "audit_summary": {
            "timestamp_utc": timestamp_utc,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "input": {**decision.audit_summary, **audit},
        },
    }
