from __future__ import annotations

from datetime import datetime, timezone
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field

from backend.app.detection.injection_detector import detect_injection
from backend.app.detection.models import DetectionResult, DetectorType, PolicyAction
from backend.app.detection.pii_detector import detect_pii
from backend.app.engine.policy_engine import evaluate_policy

app = FastAPI()

MOCK_LLM_URL = "http://localhost:8001/v1/chat/completions"
TIMEOUT_SECONDS = 10
POLICY_PATH = Path(__file__).resolve().parents[3] / "policies" / "policy.yaml"


class ProxyRequest(BaseModel):
    message: str
    policy_id: str = "default"


class ProxyResponse(BaseModel):
    request_id: str
    action: str
    reason_code: str | None
    reasons: list[str] = Field(default_factory=list)
    input_action: str
    output_action: str | None = None
    content: str | None
    audit_summary: dict[str, Any] = Field(default_factory=dict)


def _merge_detections(text: str) -> list[DetectionResult]:
    return sorted(
        [*detect_pii(text), *detect_injection(text)],
        key=lambda item: (item.start, item.end),
    )


def _resolve_reason_code(reasons: list[str]) -> str | None:
    return reasons[0] if reasons else None


def _severity(action: str) -> int:
    order = {
        PolicyAction.ALLOW.value: 1,
        PolicyAction.WARN.value: 2,
        PolicyAction.MASK.value: 3,
        PolicyAction.BLOCK.value: 4,
    }
    return order.get(action, 0)


def _final_action(input_action: str, output_action: str) -> str:
    return input_action if _severity(input_action) >= _severity(output_action) else output_action


def _audit_from_detections(
    action: str,
    reasons: list[str],
    detections: list[DetectionResult],
) -> dict[str, Any]:
    return {
        "action": action,
        "reasons": reasons,
        "pii_detected": any(item.detector_type == DetectorType.PII for item in detections),
        "injection_detected": any(item.detector_type == DetectorType.INJECTION for item in detections),
        "total_detections": len(detections),
    }


@app.post("/proxy/chat")
async def proxy_chat(req: ProxyRequest):
    started = time.perf_counter()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    request_id = str(uuid.uuid4())
    input_detections = _merge_detections(req.message)
    input_decision = evaluate_policy(req.message, input_detections, POLICY_PATH)
    input_action = input_decision.final_action.value
    input_audit = _audit_from_detections(input_action, input_decision.reasons, input_detections)

    if input_action == PolicyAction.BLOCK.value:
        return ProxyResponse(
            request_id=request_id,
            action=PolicyAction.BLOCK.value,
            reason_code=_resolve_reason_code(input_decision.reasons),
            reasons=input_decision.reasons,
            input_action=input_action,
            output_action=None,
            content=None,
            audit_summary={
                "timestamp_utc": timestamp_utc,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "input": {**input_decision.audit_summary, **input_audit},
                "output": None,
            },
        )

    processed_message = input_decision.masked_text or req.message

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            llm_resp = await client.post(
                MOCK_LLM_URL,
                json={"messages": [{"role": "user", "content": processed_message}]},
            )
        llm_resp.raise_for_status()
        llm_payload = llm_resp.json()
        llm_content = str(llm_payload["choices"][0]["message"]["content"])
    except httpx.TimeoutException:
        return ProxyResponse(
            request_id=request_id,
            action="ERROR",
            reason_code="TIMEOUT",
            reasons=["TIMEOUT"],
            input_action=input_action,
            output_action=None,
            content=None,
            audit_summary={
                "timestamp_utc": timestamp_utc,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "input": {**input_decision.audit_summary, **input_audit},
                "output": None,
            },
        )
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        return ProxyResponse(
            request_id=request_id,
            action="ERROR",
            reason_code="UPSTREAM_ERROR",
            reasons=["UPSTREAM_ERROR"],
            input_action=input_action,
            output_action=None,
            content=None,
            audit_summary={
                "timestamp_utc": timestamp_utc,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "input": {**input_decision.audit_summary, **input_audit},
                "output": None,
            },
        )

    output_detections = _merge_detections(llm_content)
    output_decision = evaluate_policy(llm_content, output_detections, POLICY_PATH)
    output_action = output_decision.final_action.value
    output_audit = _audit_from_detections(output_action, output_decision.reasons, output_detections)

    if output_action == PolicyAction.BLOCK.value:
        return ProxyResponse(
            request_id=request_id,
            action=PolicyAction.BLOCK.value,
            reason_code=_resolve_reason_code(output_decision.reasons),
            reasons=output_decision.reasons,
            input_action=input_action,
            output_action=output_action,
            content=None,
            audit_summary={
                "timestamp_utc": timestamp_utc,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "input": {**input_decision.audit_summary, **input_audit},
                "output": {**output_decision.audit_summary, **output_audit},
            },
        )

    safe_content = output_decision.masked_text or llm_content
    final_action = _final_action(input_action, output_action)
    all_reasons = sorted(set(input_decision.reasons + output_decision.reasons))

    return ProxyResponse(
        request_id=request_id,
        action=final_action,
        reason_code=_resolve_reason_code(all_reasons),
        reasons=all_reasons,
        input_action=input_action,
        output_action=output_action,
        content=safe_content,
        audit_summary={
            "timestamp_utc": timestamp_utc,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "input": {**input_decision.audit_summary, **input_audit},
            "output": {**output_decision.audit_summary, **output_audit},
        },
    )
