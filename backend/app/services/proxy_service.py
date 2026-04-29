from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.detection.injection_detector import detect_injection
from backend.app.detection.models import DetectionResult, DetectorType, PolicyAction
from backend.app.detection.pii_detector import detect_pii
from backend.app.engine.policy_engine import evaluate_policy
from backend.app.schemas.proxy import ProxyRequest, ProxyResponse
from backend.app.services.audit_service import save_audit_log
from backend.app.services.llm_service import UpstreamRequestError, UpstreamTimeoutError, call_upstream_llm


POLICY_PATH = Path(__file__).resolve().parents[3] / "policies" / "policy.yaml"


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


def _build_audit_summary(
    timestamp_utc: str,
    started: float,
    *,
    final_action: str,
    reason_codes: list[str],
    input_action: str,
    output_action: str | None,
    input_summary: dict[str, Any],
    output_summary: dict[str, Any] | None,
    upstream_call: bool,
) -> dict[str, Any]:
    return {
        "timestamp_utc": timestamp_utc,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "action": final_action,
        "reason_codes": reason_codes,
        "input_action": input_action,
        "output_action": output_action,
        "upstream_call": upstream_call,
        "input": input_summary,
        "output": output_summary,
    }


def _response(
    req: ProxyRequest,
    request_id: str,
    action: str,
    reason_codes: list[str],
    input_action: str,
    output_action: str | None,
    content: str | None,
    audit_summary: dict[str, Any],
) -> ProxyResponse:
    save_audit_log(request_id, req.user_id, audit_summary)
    return ProxyResponse(
        request_id=request_id,
        action=action,
        reason_code=_resolve_reason_code(reason_codes),
        reasons=reason_codes,
        input_action=input_action,
        output_action=output_action,
        content=content,
        audit_summary=audit_summary,
    )


async def process_proxy_chat(req: ProxyRequest) -> ProxyResponse:
    started = time.perf_counter()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    request_id = str(uuid.uuid4())

    input_detections = _merge_detections(req.message)
    input_decision = evaluate_policy(req.message, input_detections, POLICY_PATH)
    input_action = input_decision.final_action.value
    input_audit = _audit_from_detections(input_action, input_decision.reasons, input_detections)
    input_summary = {**input_decision.audit_summary, **input_audit}

    if input_action == PolicyAction.BLOCK.value:
        audit_summary = _build_audit_summary(
            timestamp_utc,
            started,
            final_action=PolicyAction.BLOCK.value,
            reason_codes=input_decision.reasons,
            input_action=input_action,
            output_action=None,
            input_summary=input_summary,
            output_summary=None,
            upstream_call=False,
        )
        return _response(
            req,
            request_id,
            PolicyAction.BLOCK.value,
            input_decision.reasons,
            input_action,
            None,
            None,
            audit_summary,
        )

    processed_message = input_decision.masked_text or req.message

    try:
        llm_content = await call_upstream_llm(processed_message, model=req.model)
    except UpstreamTimeoutError:
        reasons = ["TIMEOUT"]
        audit_summary = _build_audit_summary(
            timestamp_utc,
            started,
            final_action="ERROR",
            reason_codes=reasons,
            input_action=input_action,
            output_action=None,
            input_summary=input_summary,
            output_summary=None,
            upstream_call=True,
        )
        return _response(req, request_id, "ERROR", reasons, input_action, None, None, audit_summary)
    except UpstreamRequestError:
        reasons = ["UPSTREAM_ERROR"]
        audit_summary = _build_audit_summary(
            timestamp_utc,
            started,
            final_action="ERROR",
            reason_codes=reasons,
            input_action=input_action,
            output_action=None,
            input_summary=input_summary,
            output_summary=None,
            upstream_call=True,
        )
        return _response(req, request_id, "ERROR", reasons, input_action, None, None, audit_summary)

    output_detections = _merge_detections(llm_content)
    output_decision = evaluate_policy(llm_content, output_detections, POLICY_PATH)
    output_action = output_decision.final_action.value
    output_audit = _audit_from_detections(output_action, output_decision.reasons, output_detections)
    output_summary = {**output_decision.audit_summary, **output_audit}

    if output_action == PolicyAction.BLOCK.value:
        audit_summary = _build_audit_summary(
            timestamp_utc,
            started,
            final_action=PolicyAction.BLOCK.value,
            reason_codes=output_decision.reasons,
            input_action=input_action,
            output_action=output_action,
            input_summary=input_summary,
            output_summary=output_summary,
            upstream_call=True,
        )
        return _response(
            req,
            request_id,
            PolicyAction.BLOCK.value,
            output_decision.reasons,
            input_action,
            output_action,
            None,
            audit_summary,
        )

    safe_content = output_decision.masked_text or llm_content
    final_action = _final_action(input_action, output_action)
    all_reasons = sorted(set(input_decision.reasons + output_decision.reasons))
    audit_summary = _build_audit_summary(
        timestamp_utc,
        started,
        final_action=final_action,
        reason_codes=all_reasons,
        input_action=input_action,
        output_action=output_action,
        input_summary=input_summary,
        output_summary=output_summary,
        upstream_call=True,
    )

    return _response(
        req,
        request_id,
        final_action,
        all_reasons,
        input_action,
        output_action,
        safe_content,
        audit_summary,
    )
