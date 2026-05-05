from __future__ import annotations

import json
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

from fastapi import HTTPException

from backend.app.detection.injection_detector import detect_injection
from backend.app.detection.models import DetectionResult, DetectorType, PolicyAction
from backend.app.detection.pii_detector import detect_pii
from backend.app.engine.masking import apply_masking
from backend.app.engine.policy_engine import evaluate_policy
from backend.app.models.lightweight_classifier import detect_model_risk
from backend.app.schemas.proxy import ProxyRequest, ProxyResponse
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
_SECRET_PATTERNS = (
    re.compile(r"authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE),
    re.compile(r"api[-_ ]?key\s*[:=]\s*[A-Za-z0-9._\-]+", re.IGNORECASE),
    re.compile(r"cookie\s*:\s*[^;\n]+", re.IGNORECASE),
)


def _merge_detections(text: str) -> list[DetectionResult]:
    # 정규식, 룰, 경량 모델 결과를 합쳐 정책 엔진으로 보냅니다.
    return sorted(
        [*detect_pii(text), *detect_injection(text), *detect_model_risk(text)],
        key=lambda item: (
            item.start if item.start is not None else 10**9,
            item.end if item.end is not None else 10**9,
            item.reason_code,
        ),
    )


def _resolve_reason_code(reasons: list[str]) -> str | None:
    return reasons[0] if reasons else None


def _sanitize_secret_preview(text: str) -> str:
    sanitized = text
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


def _preview_text(text: str, detections: list[DetectionResult]) -> str:
    pii_detections = [
        item
        for item in detections
        if item.detector_type == DetectorType.PII and item.start is not None and item.end is not None and item.matched_text
    ]
    preview = apply_masking(text, pii_detections) if pii_detections else text
    preview = _sanitize_secret_preview(preview)
    preview = re.sub(r"\s+", " ", preview).strip()
    return preview[:160]


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
    pii_types = sorted({item.label for item in detections if item.detector_type == DetectorType.PII})
    return {
        "action": action,
        "reasons": reasons,
        "pii_detected": any(item.detector_type == DetectorType.PII for item in detections),
        "injection_detected": any(item.detector_type == DetectorType.INJECTION for item in detections),
        "model_detected": any(item.detector_type == DetectorType.MODEL for item in detections),
        "total_detections": len(detections),
        "pii_types": pii_types,
        "detector_counts": {
            "pii": sum(1 for item in detections if item.detector_type == DetectorType.PII),
            "injection": sum(1 for item in detections if item.detector_type == DetectorType.INJECTION),
            "model": sum(1 for item in detections if item.detector_type == DetectorType.MODEL),
        },
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
    # 감사 요약에는 보안 판단에 필요한 메타데이터만 남깁니다.
    # 원문 프롬프트와 원문 응답은 로그 저장 전에 의도적으로 제외합니다.
    return {
        "timestamp_utc": timestamp_utc,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "action": final_action,
        "reason_codes": reason_codes,
        "input_action": input_action,
        "output_action": output_action,
        "upstream_call": upstream_call,
        "policy_version": (input_summary or {}).get("policy_version") or (output_summary or {}).get("policy_version"),
        "model_version": (input_summary or {}).get("model_version") or (output_summary or {}).get("model_version"),
        "input": input_summary,
        "output": output_summary,
    }


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


async def process_proxy_chat(req: ProxyRequest) -> ProxyResponse:
    started = time.perf_counter()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    request_id = str(uuid.uuid4())
    policy_path = resolve_policy_path(req.policy_id)

    # 1단계: 외부 LLM을 호출하기 전에 입력 프롬프트를 먼저 검사합니다.
    input_detections = _merge_detections(req.message)
    input_decision = evaluate_policy(req.message, input_detections, policy_path)
    input_action = input_decision.final_action.value
    input_audit = _audit_from_detections(input_action, input_decision.reasons, input_detections)
    input_summary = {
        **input_decision.audit_summary,
        **input_audit,
        "masked_preview": _preview_text(req.message, input_detections),
    }

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
    output_detections = _merge_detections(llm_content)
    output_decision = evaluate_policy(llm_content, output_detections, policy_path)
    output_action = output_decision.final_action.value
    output_audit = _audit_from_detections(output_action, output_decision.reasons, output_detections)
    output_summary = {
        **output_decision.audit_summary,
        **output_audit,
        "masked_preview": _preview_text(llm_content, output_detections),
    }

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


async def process_proxy_chat_stream(req: ProxyRequest) -> AsyncIterator[str]:
    started = time.perf_counter()
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    request_id = str(uuid.uuid4())
    policy_path = resolve_policy_path(req.policy_id)

    input_detections = _merge_detections(req.message)
    input_decision = evaluate_policy(req.message, input_detections, policy_path)
    input_action = input_decision.final_action.value
    input_audit = _audit_from_detections(input_action, input_decision.reasons, input_detections)
    input_summary = {
        **input_decision.audit_summary,
        **input_audit,
        "masked_preview": _preview_text(req.message, input_detections),
    }

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
            output_action=None,
            input_summary=input_summary,
            output_summary=None,
            upstream_call=False,
        )
        response = _response(
            req,
            request_id,
            PolicyAction.BLOCK.value,
            input_decision.reasons,
            input_action,
            None,
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
    output_detections = _merge_detections(llm_content)
    output_decision = evaluate_policy(llm_content, output_detections, policy_path)
    output_action = output_decision.final_action.value
    output_audit = _audit_from_detections(output_action, output_decision.reasons, output_detections)
    output_summary = {
        **output_decision.audit_summary,
        **output_audit,
        "masked_preview": _preview_text(llm_content, output_detections),
    }

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
