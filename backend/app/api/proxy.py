from __future__ import annotations
from fastapi.middleware.cors import CORSMiddleware

import logging
import os
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse

from backend.app.config import get_detection_settings
from backend.app.detection.models import PolicyAction
from backend.app.engine.policy_engine import evaluate_policy
from backend.app.schemas.admin import (
    AdminStatsResponse,
    ReasonCodeStatItem,
    RecentBlockItem,
)
from backend.app.schemas.proxy import (
    ChatCompletionRequest,
    ProxyAnalyzeResponse,
    ProxyRequest,
    ProxyResponse,
)
from backend.app.schemas.upstream import UpstreamConfigResponse
from backend.app.services.audit_service import (
    get_admin_stats,
    get_reason_code_stats,
    get_recent_block_history,
    save_audit_log,
)
from backend.app.services.llm_service import get_upstream_config_summary
from backend.app.services.proxy_service import (
    POLICY_PATH,
    _detect_text,
    _audit_from_detections,
    _combine_reason_codes,
    _output_summary_from_validator,
    _resolve_reason_code,
    _skipped_output_summary,
    _skipped_validator_summary,
    _validator_audit_summary,
    _validator_public_reasons,
    process_proxy_analyze,
    process_proxy_chat,
    process_proxy_chat_stream,
)
from backend.app.validator import ValidatorAgent, resolve_final_action


app = FastAPI()
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def log_detection_configuration() -> None:
    settings = get_detection_settings()
    logger.info("Detection mode: %s", settings.detection_mode)
    logger.info("Model detector enabled: %s", settings.enable_model_detector)

def _admin_api_token() -> str:
    return os.getenv("ADMIN_API_TOKEN", "dev-admin-token")


def _require_admin_token(
    x_admin_token: str | None = Header(default=None),
) -> None:
    if x_admin_token is not None and not isinstance(x_admin_token, str):
        return
    if x_admin_token != _admin_api_token():
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post("/proxy/chat")
async def proxy_chat(req: ProxyRequest) -> ProxyResponse:
    return await process_proxy_chat(req)


@app.post("/proxy/analyze")
async def proxy_analyze(req: ProxyRequest) -> ProxyAnalyzeResponse:
    return await process_proxy_analyze(req)


@app.post("/proxy/chat/stream")
async def proxy_chat_stream(req: ProxyRequest) -> StreamingResponse:
    return StreamingResponse(
        process_proxy_chat_stream(req),
        media_type="text/event-stream",
    )


@app.get("/admin/stats")
async def admin_stats(
    x_admin_token: str | None = Header(default=None),
) -> AdminStatsResponse:
    _require_admin_token(x_admin_token)
    return AdminStatsResponse(**get_admin_stats())


@app.get("/admin/recent-blocks")
async def admin_recent_blocks(
    limit: int = 10,
    x_admin_token: str | None = Header(default=None),
) -> list[RecentBlockItem]:
    _require_admin_token(x_admin_token)
    return [
        RecentBlockItem(**entry)
        for entry in get_recent_block_history(limit=limit)
    ]


@app.get("/admin/reason-codes")
async def admin_reason_codes(
    x_admin_token: str | None = Header(default=None),
) -> list[ReasonCodeStatItem]:
    _require_admin_token(x_admin_token)
    return [
        ReasonCodeStatItem(**entry)
        for entry in get_reason_code_stats()
    ]


@app.get("/admin/upstream-config")
async def admin_upstream_config(
    x_admin_token: str | None = Header(default=None),
) -> UpstreamConfigResponse:
    _require_admin_token(x_admin_token)
    return UpstreamConfigResponse(**get_upstream_config_summary())


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest) -> dict:
    started = time.perf_counter()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    request_id = str(uuid.uuid4())
    user_messages = [
        message.content
        for message in req.messages
        if message.role == "user"
    ]
    message = "\n".join(user_messages)

    hybrid_result = _detect_text(message)
    detections = hybrid_result.detections
    decision = evaluate_policy(message, detections, POLICY_PATH)
    action = decision.final_action.value
    audit = _audit_from_detections(
        action,
        decision.reasons,
        detections,
        hybrid_result=hybrid_result,
    )
    content = (
        None
        if action == PolicyAction.BLOCK.value
        else decision.masked_text or "mock response"
    )

    validator_summary = _skipped_validator_summary(PolicyAction.BLOCK.value)
    output_summary = _skipped_output_summary()
    output_action = PolicyAction.BLOCK.value if action == PolicyAction.BLOCK.value else PolicyAction.ALLOW.value
    final_action = action
    final_reasons = decision.reasons

    if action != PolicyAction.BLOCK.value and content is not None:
        output_hybrid = _detect_text(content)
        output_detections = output_hybrid.detections
        output_decision = evaluate_policy(content, output_detections, POLICY_PATH)
        validator_summary = ValidatorAgent(POLICY_PATH).validate_output(
            content,
            {**decision.audit_summary, **audit, "action": action},
            decision,
            request_context={
                "policy_path": POLICY_PATH,
                "input_action": action,
                "input_detections": detections,
                "output_hybrid": output_hybrid,
                "output_policy_decision": output_decision,
            },
        )
        output_action = validator_summary["output_action"]
        output_reasons = _validator_public_reasons(validator_summary)
        output_audit = _audit_from_detections(
            output_action,
            output_reasons,
            output_detections,
            hybrid_result=output_hybrid,
        )
        output_summary = _output_summary_from_validator(
            output_action,
            validator_summary,
            output_decision.audit_summary,
            output_audit,
        )
        final_action = resolve_final_action(action, output_action)
        final_reasons = _combine_reason_codes(decision.reasons, output_reasons)
        if output_action == PolicyAction.BLOCK.value:
            content = None
            final_action = PolicyAction.BLOCK.value
        else:
            content = validator_summary.get("masked_text") or content

    audit_summary = {
        "timestamp_utc": timestamp_utc,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "action": final_action,
        "final_action": final_action,
        "reason_codes": final_reasons,
        "input_action": action,
        "output_action": output_action,
        "upstream_call": False,
        "input": {
            **decision.audit_summary,
            **audit,
        },
        "output": output_summary,
        "validator": _validator_audit_summary(validator_summary),
    }
    if "hybrid_detection" in audit:
        audit_summary["hybrid_detection"] = {
            "input": audit["hybrid_detection"],
        }
    if isinstance(output_summary, dict) and "hybrid_detection" in output_summary:
        audit_summary.setdefault("hybrid_detection", {})["output"] = output_summary["hybrid_detection"]

    save_audit_log(request_id, "openai-compatible", audit_summary)

    return {
        "id": request_id,
        "object": "chat.completion",
        "model": req.model,
        "action": final_action,
        "reason_code": _resolve_reason_code(final_reasons),
        "reasons": final_reasons,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": (
                    "content_filter"
                    if final_action == PolicyAction.BLOCK.value
                    else "stop"
                ),
            }
        ],
        "audit_summary": audit_summary,
    }
