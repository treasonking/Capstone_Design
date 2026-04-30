from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI

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
)

# FastAPI entrypoint that exposes both the user-facing proxy route and
# the admin/demo endpoints used during evaluation.
app = FastAPI()


@app.post("/proxy/chat")
async def proxy_chat(req: ProxyRequest) -> ProxyResponse:
    return await process_proxy_chat(req)


@app.get("/admin/stats")
async def admin_stats() -> AdminStatsResponse:
    return AdminStatsResponse(**get_admin_stats())


@app.get("/admin/recent-blocks")
async def admin_recent_blocks(limit: int = 10) -> list[RecentBlockItem]:
    return [RecentBlockItem(**entry) for entry in get_recent_block_history(limit=limit)]


@app.get("/admin/reason-codes")
async def admin_reason_codes() -> list[ReasonCodeStatItem]:
    return [ReasonCodeStatItem(**entry) for entry in get_reason_code_stats()]


@app.get("/admin/upstream-config")
async def admin_upstream_config() -> UpstreamConfigResponse:
    return UpstreamConfigResponse(**get_upstream_config_summary())


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    """OpenAI-compatible mock endpoint for local policy demos."""
    started = time.perf_counter()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    request_id = str(uuid.uuid4())
    user_messages = [message.content for message in req.messages if message.role == "user"]
    message = "\n".join(user_messages)

    detections = _merge_detections(message)
    decision = evaluate_policy(message, detections, POLICY_PATH)
    action = decision.final_action.value
    audit = _audit_from_detections(action, decision.reasons, detections)
    # The mock endpoint mirrors the policy behavior of the main proxy so demos
    # can show filtering without needing a real upstream model.
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
