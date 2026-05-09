from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from fastapi import HTTPException

from backend.app.detection.hybrid_detector import (
    HybridDetectionResult,
    detect_hybrid,
)
from backend.app.detection.models import DetectionResult, DetectorType, PolicyAction
from backend.app.detection.reason_codes import ReasonCode, ordered_reason_codes, select_primary_reason
from backend.app.engine.policy_engine import evaluate_policy
from backend.app.schemas.proxy import DetectionPreviewItem, ProxyAnalyzeResponse, ProxyRequest, ProxyResponse
from backend.app.services.audit_service import save_audit_log
from backend.app.services.llm_service import UpstreamRequestError, UpstreamTimeoutError, call_upstream_llm, stream_upstream_llm


POLICY_DIR = Path(__file__).resolve().parents[3] / "policies"
POLICY_PATH = POLICY_DIR / "policy.yaml"
STRICT_POLICY_PATH = POLICY_DIR / "strict.yaml"
ALLOWED_POLICY_IDS = {
    "default": POLICY_PATH,
    "strict": STRICT_POLICY_PATH,
}
POLICY_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
logger = logging.getLogger(__name__)


def _detect_text(text: str) -> HybridDetectionResult:
    result = detect_hybrid(text)
    result.detections = sorted(
        result.detections,
        key=lambda item: (item.start, item.end),
    )
    return result


def _merge_detections(text: str) -> list[DetectionResult]:
    # 하이브리드 탐지는 regex/rule 결과를 기본으로 유지하고,
    # 선택형 경량 모델 신호가 있을 때만 보조 탐지 결과를 함께 합칩니다.
    return _detect_text(text).detections


def _resolve_reason_code(reasons: list[str]) -> str | None:
    return select_primary_reason(reasons) if reasons else None


def _combine_reason_codes(*reason_groups: list[str]) -> list[str]:
    combined: list[str] = []

    for group in reason_groups:
        if not group:
            continue
        combined.extend(group)

    non_safe = [
        reason
        for reason in ordered_reason_codes(combined)
        if reason != ReasonCode.SAFE_INPUT.value
    ]
    if non_safe:
        return non_safe

    return [ReasonCode.SAFE_INPUT.value]


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
    hybrid_result: HybridDetectionResult | None = None,
) -> dict[str, Any]:
    detector_results: list[dict[str, Any]] = []
    detector_counts: dict[str, int] = {}
    total_detections = len(detections)
    pii_detected = any(item.detector_type == DetectorType.PII for item in detections)
    injection_detected = any(item.detector_type == DetectorType.INJECTION for item in detections)

    if hybrid_result is not None:
        detector_counts = dict(hybrid_result.detector_counts)
        total_detections = len(detections)
        pii_detected = hybrid_result.pii_detected
        injection_detected = hybrid_result.injection_detected
        detector_results = []
        for result in hybrid_result.detector_results:
            if result.action == "SKIPPED":
                continue
            item: dict[str, Any] = {
                "detector": result.detector,
                "action": result.action,
                "reasons": result.reasons,
                "status": result.status,
            }
            if result.confidence is not None:
                item["confidence"] = round(result.confidence, 3)
            if result.detector == "llm":
                if hybrid_result.model_threshold is not None:
                    item["model_threshold"] = hybrid_result.model_threshold
                item["model_prediction_accepted"] = hybrid_result.model_prediction_accepted
                if hybrid_result.model_reason_code is not None:
                    item["model_reason_code"] = hybrid_result.model_reason_code
            detector_results.append(item)

    summary = {
        "action": action,
        "reasons": reasons,
        "pii_detected": pii_detected,
        "injection_detected": injection_detected,
        "total_detections": total_detections,
        "detector_counts": detector_counts,
        "detector_count_basis": "matched_detectors",
        "matched_detector_count": len(detector_counts),
        "applied_rule_count": len([reason for reason in reasons if reason != "SAFE_INPUT"]),
    }
    if detector_results:
        summary["detector_results"] = detector_results
    if hybrid_result is not None:
        summary["detectors_invoked"] = hybrid_result.detectors_invoked
        summary["detector_invocation_count"] = len(hybrid_result.detectors_invoked)
        hybrid_detection = {
            "model_enabled": hybrid_result.model_enabled,
            "model_status": hybrid_result.model_status,
            "fallback_used": hybrid_result.fallback_used,
        }
        if hybrid_result.fallback_used:
            hybrid_detection["fallback_reason"] = hybrid_result.model_status
        if hybrid_result.model_label is not None:
            hybrid_detection["model_label"] = hybrid_result.model_label
        if hybrid_result.model_confidence is not None:
            hybrid_detection["model_confidence"] = hybrid_result.model_confidence
        if hybrid_result.model_threshold is not None:
            hybrid_detection["model_threshold"] = hybrid_result.model_threshold
        hybrid_detection["model_prediction_accepted"] = hybrid_result.model_prediction_accepted
        if hybrid_result.model_reason_code is not None:
            hybrid_detection["model_reason_code"] = hybrid_result.model_reason_code
        summary["hybrid_detection"] = hybrid_detection
    return summary


def _skipped_output_summary() -> dict[str, Any]:
    return {
        "total_detections": 0,
        "detector_counts": {},
        "applied_rule_count": 0,
        "action": "SKIPPED",
        "reasons": ["UPSTREAM_NOT_CALLED"],
        "pii_detected": False,
        "injection_detected": False,
    }


def _top_level_hybrid_detection(
    input_summary: dict[str, Any],
    output_summary: dict[str, Any] | None,
) -> dict[str, Any] | None:
    hybrid_detection: dict[str, Any] = {}
    input_hybrid = input_summary.get("hybrid_detection")
    if input_hybrid is not None:
        hybrid_detection["input"] = input_hybrid
    output_hybrid = (output_summary or {}).get("hybrid_detection")
    if output_hybrid is not None:
        hybrid_detection["output"] = output_hybrid
    return hybrid_detection or None


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
    # 감사 요약에는 보안 판단에 필요한 메타데이터만 남깁니다.
    # 원문 프롬프트와 원문 응답은 로그 저장 전에 의도적으로 제외합니다.
    audit_summary = {
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
    hybrid_detection = _top_level_hybrid_detection(input_summary, output_summary)
    if hybrid_detection is not None:
        audit_summary["hybrid_detection"] = hybrid_detection
    return audit_summary


def resolve_policy_path(policy_id: str) -> Path:
    normalized_policy_id = (policy_id or "default").strip()
    if not POLICY_ID_PATTERN.fullmatch(normalized_policy_id):
        raise HTTPException(status_code=400, detail="Invalid policy_id format.")

    policy_path = ALLOWED_POLICY_IDS.get(normalized_policy_id)
    if policy_path is None:
        raise HTTPException(status_code=400, detail="Unsupported policy_id.")

    return policy_path


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


def _sse_event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _recommendation(
    action: str,
    *,
    pii_detected: bool,
    injection_detected: bool,
) -> str:
    if action == PolicyAction.BLOCK.value:
        if injection_detected:
            return "프롬프트 인젝션 위험이 있어 AI로 전송하지 않는 것을 권장합니다."
        return "차단 정책에 해당하므로 내용을 수정한 뒤 다시 검사하는 것을 권장합니다."
    if action == PolicyAction.MASK.value:
        return "민감정보가 포함되어 있어 마스킹된 문장으로 전송하는 것을 권장합니다."
    if action == PolicyAction.WARN.value:
        return "주의가 필요한 요청입니다. 담당자가 내용을 확인한 뒤 전송하는 것을 권장합니다."
    if pii_detected:
        return "민감정보 가능성이 있으므로 전송 전 내용을 한 번 더 확인하는 것을 권장합니다."
    return "안전한 요청으로 판단됩니다."


def _preview_items(detections: list[DetectionResult]) -> list[DetectionPreviewItem]:
    return [
        DetectionPreviewItem(
            detector_type=item.detector_type.value,
            category=item.category,
            reason_code=item.reason_code,
            detector_source=item.detector_name,
            confidence=round(min(item.score, 1.0), 3),
            start=item.start,
            end=item.end,
        )
        for item in detections
    ]


async def process_proxy_analyze(req: ProxyRequest) -> ProxyAnalyzeResponse:
    started = time.perf_counter()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    request_id = str(uuid.uuid4())
    policy_path = resolve_policy_path(req.policy_id)

    input_hybrid = _detect_text(req.message)
    input_detections = input_hybrid.detections
    input_decision = evaluate_policy(req.message, input_detections, policy_path)
    input_action = input_decision.final_action.value
    input_audit = _audit_from_detections(
        input_action,
        input_decision.reasons,
        input_detections,
        hybrid_result=input_hybrid,
    )
    input_summary = {**input_decision.audit_summary, **input_audit}
    audit_summary = _build_audit_summary(
        timestamp_utc,
        started,
        final_action=input_action,
        reason_codes=input_decision.reasons,
        input_action=input_action,
        output_action="SKIPPED",
        input_summary=input_summary,
        output_summary=_skipped_output_summary(),
        upstream_call=False,
    )
    pii_detected = bool(input_summary.get("pii_detected", False))
    injection_detected = bool(input_summary.get("injection_detected", False))

    return ProxyAnalyzeResponse(
        request_id=request_id,
        action=input_action,
        reason_code=_resolve_reason_code(input_decision.reasons),
        reasons=input_decision.reasons,
        pii_detected=pii_detected,
        injection_detected=injection_detected,
        masked_text=input_decision.masked_text,
        should_call_llm=input_action != PolicyAction.BLOCK.value,
        upstream_call=False,
        recommendation=_recommendation(
            input_action,
            pii_detected=pii_detected,
            injection_detected=injection_detected,
        ),
        detector_results=_preview_items(input_detections),
        audit_summary=audit_summary,
    )


async def process_proxy_chat(req: ProxyRequest) -> ProxyResponse:
    started = time.perf_counter()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    request_id = str(uuid.uuid4())
    policy_path = resolve_policy_path(req.policy_id)

    # 1단계: 외부 LLM을 호출하기 전에 입력 프롬프트를 먼저 검사합니다.
    input_hybrid = _detect_text(req.message)
    input_detections = input_hybrid.detections
    input_decision = evaluate_policy(req.message, input_detections, policy_path)
    input_action = input_decision.final_action.value
    input_audit = _audit_from_detections(
        input_action,
        input_decision.reasons,
        input_detections,
        hybrid_result=input_hybrid,
    )
    input_summary = {**input_decision.audit_summary, **input_audit}

    if input_action == PolicyAction.BLOCK.value:
        audit_summary = _build_audit_summary(
            timestamp_utc,
            started,
            final_action=PolicyAction.BLOCK.value,
            reason_codes=input_decision.reasons,
            input_action=input_action,
            output_action=PolicyAction.BLOCK.value,
            input_summary=input_summary,
            output_summary=_skipped_output_summary(),
            upstream_call=False,
        )
        return _response(
            req,
            request_id,
            PolicyAction.BLOCK.value,
            input_decision.reasons,
            input_action,
            PolicyAction.BLOCK.value,
            None,
            audit_summary,
        )

    # 정책이 마스킹을 요구하면 원문 대신 마스킹된 프롬프트만 전달합니다.
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
    except UpstreamRequestError as exc:
        reasons = [exc.reason_code]
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

    # 2단계: 모델 응답도 신뢰하지 않고 다시 검사합니다.
    output_hybrid = _detect_text(llm_content)
    output_detections = output_hybrid.detections
    output_decision = evaluate_policy(llm_content, output_detections, policy_path)
    output_action = output_decision.final_action.value
    output_audit = _audit_from_detections(
        output_action,
        output_decision.reasons,
        output_detections,
        hybrid_result=output_hybrid,
    )
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

    # 입력과 출력에 각각 정책 결과가 있으면 더 강한 조치를 최종 action으로 반환합니다.
    safe_content = output_decision.masked_text or llm_content
    final_action = _final_action(input_action, output_action)
    all_reasons = _combine_reason_codes(input_decision.reasons, output_decision.reasons)
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


async def process_proxy_chat_stream(req: ProxyRequest) -> AsyncIterator[str]:
    started = time.perf_counter()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    request_id = str(uuid.uuid4())
    policy_path = resolve_policy_path(req.policy_id)

    input_hybrid = _detect_text(req.message)
    input_detections = input_hybrid.detections
    input_decision = evaluate_policy(req.message, input_detections, policy_path)
    input_action = input_decision.final_action.value
    input_audit = _audit_from_detections(
        input_action,
        input_decision.reasons,
        input_detections,
        hybrid_result=input_hybrid,
    )
    input_summary = {**input_decision.audit_summary, **input_audit}

    yield _sse_event(
        "policy",
        {
            "request_id": request_id,
            "input_action": input_action,
            "reasons": input_decision.reasons,
        },
    )

    if input_action == PolicyAction.BLOCK.value:
        audit_summary = _build_audit_summary(
            timestamp_utc,
            started,
            final_action=PolicyAction.BLOCK.value,
            reason_codes=input_decision.reasons,
            input_action=input_action,
            output_action=PolicyAction.BLOCK.value,
            input_summary=input_summary,
            output_summary=_skipped_output_summary(),
            upstream_call=False,
        )
        response = _response(
            req,
            request_id,
            PolicyAction.BLOCK.value,
            input_decision.reasons,
            input_action,
            PolicyAction.BLOCK.value,
            None,
            audit_summary,
        )
        yield _sse_event("done", response.model_dump())
        return

    processed_message = input_decision.masked_text or req.message
    output_chunks: list[str] = []

    try:
        async for chunk in stream_upstream_llm(processed_message, model=req.model):
            output_chunks.append(chunk)
            yield _sse_event("token", {"request_id": request_id, "content": chunk})
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
        response = _response(req, request_id, "ERROR", reasons, input_action, None, None, audit_summary)
        yield _sse_event("error", response.model_dump())
        return
    except UpstreamRequestError as exc:
        reasons = [exc.reason_code]
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
        response = _response(req, request_id, "ERROR", reasons, input_action, None, None, audit_summary)
        yield _sse_event("error", response.model_dump())
        return

    llm_content = "".join(output_chunks)
    output_hybrid = _detect_text(llm_content)
    output_detections = output_hybrid.detections
    output_decision = evaluate_policy(llm_content, output_detections, policy_path)
    output_action = output_decision.final_action.value
    output_audit = _audit_from_detections(
        output_action,
        output_decision.reasons,
        output_detections,
        hybrid_result=output_hybrid,
    )
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
        response = _response(
            req,
            request_id,
            PolicyAction.BLOCK.value,
            output_decision.reasons,
            input_action,
            output_action,
            None,
            audit_summary,
        )
        yield _sse_event("done", response.model_dump())
        return

    final_action = _final_action(input_action, output_action)
    all_reasons = _combine_reason_codes(input_decision.reasons, output_decision.reasons)
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
    response = _response(
        req,
        request_id,
        final_action,
        all_reasons,
        input_action,
        output_action,
        output_decision.masked_text or llm_content,
        audit_summary,
    )
    yield _sse_event("done", response.model_dump())
