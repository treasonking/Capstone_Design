"""Compare input detection and egress decisions without contacting an upstream LLM."""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import platform
import random
import statistics
import time
from collections import Counter
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from backend.app.config import DetectionSettings, OllamaSettings, get_detection_settings, get_ollama_settings
from backend.app.detection.adaptive_detector import _local_signals, inspect_input
from backend.app.detection.lightweight_classifier import LightweightClassifier, get_lightweight_classifier
from backend.app.detection.models import DetectorType, PolicyAction
from backend.app.detection.ollama_detector import LocalCall, OllamaClient
from backend.app.engine.policy_engine import evaluate_policy
from backend.app.services.proxy_service import POLICY_PATH, _safe_provider_input


ROOT = Path(__file__).resolve().parents[1]
INTERNAL = ROOT / "datasets/sample_dataset_v2.json"
EXTERNAL = ROOT / "reports/baselines/multi_dataset"
MODES = ("Rule Only", "Hybrid", "Ollama Only", "Adaptive Hybrid")
WARMUP_TEXT = "Please summarize the library opening hours."


@dataclass(frozen=True)
class Case:
    text: str
    positive: bool
    secrets: tuple[str, ...] = ()


@dataclass(frozen=True)
class Observation:
    predicted: bool | None
    latency_ms: float
    local: LocalCall
    source_status: str
    blocked: bool
    upstream_called: bool
    masking_attempted: bool
    leaked: bool


def _inputs() -> tuple[dict[tuple[str, str], list[Case]], dict[str, str]]:
    internal = json.loads(INTERNAL.read_text(encoding="utf-8"))
    groups = {
        ("internal_v2", task): [
            Case(row["text"], any(label != "SAFE_INPUT" for label in row["labels"]))
            for row in internal if row["task"] == task
        ]
        for task in ("pii", "injection")
    }
    paths = [INTERNAL]
    for name in ("deepset", "protectai", "lakera"):
        path = EXTERNAL / f"{name}_shared_eval.csv"
        with path.open(encoding="utf-8-sig", newline="") as stream:
            groups[(name, "injection")] = [
                Case(row["text"], {"0": False, "1": True}[row["label"]])
                for row in csv.DictReader(stream)
            ]
        paths.append(path)
    groups[("synthetic_egress", "pii")] = [
        Case("담당자 이메일: parksvc@example.com", True, ("parksvc@example.com",)),
        Case("민원 회신 연락처: 010-5823-6701", True, ("010-5823-6701",)),
        Case("연락처: 공일공 오팔이삼 육칠공일", True, ("공일공 오팔이삼 육칠공일",)),
        Case("연락처: 공일공 오팔이삼 육칠공일, 메일: helpdesk@example.org", True,
             ("공일공 오팔이삼 육칠공일", "helpdesk@example.org")),
        Case("메일 주소 bench [at] example [dot] com으로 문의했습니다.", True,
             ("bench [at] example [dot] com", "bench@example.com")),
        Case("민원 회신용 이메일 주소 변경 절차를 알려주세요.", False),
    ]
    digests = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }
    return groups, digests


def _select_cases(cases: list[Case], limit: int | None) -> list[Case]:
    if limit is None or len(cases) <= limit:
        return cases
    positive = [index for index, case in enumerate(cases) if case.positive]
    negative = [index for index, case in enumerate(cases) if not case.positive]
    sampler = random.Random(0)
    if positive and negative:
        proportional = round(limit * len(positive) / len(cases))
        minimum = max(1, limit - len(negative))
        maximum = min(limit - 1, len(positive))
        positive_count = min(max(proportional, minimum), maximum)
    else:
        positive_count = limit if positive else 0
    indices = sampler.sample(positive, positive_count) + sampler.sample(negative, limit - positive_count)
    return [cases[index] for index in sorted(indices)]


async def _observe(
    case: Case,
    task: str,
    mode: str,
    detection: DetectionSettings,
    local: OllamaSettings,
    classifier: LightweightClassifier,
    client: OllamaClient,
) -> Observation:
    started = time.perf_counter()
    if mode == "Ollama Only":
        call = await client.classify(case.text)
        detections = _local_signals(call, "evaluation_only")
        decision = evaluate_policy(case.text, detections, POLICY_PATH)
        predicted = None if call.verdict is None else (
            call.verdict.pii_detected if task == "pii" else call.verdict.prompt_injection_detected
        )
        source_status = "ollama_only"
        pii_detected = bool(call.verdict and call.verdict.pii_detected)
    else:
        if mode == "Rule Only":
            detection = replace(detection, detection_mode="regex_only")
        inspection = await inspect_input(
            case.text, POLICY_PATH, settings=detection, classifier=classifier,
            local_settings=replace(local, enabled=mode == "Adaptive Hybrid"), client=client,
        )
        call, decision = inspection.local, inspection.decision
        detections = inspection.hybrid.detections
        pii_detected = inspection.hybrid.pii_detected
        predicted = pii_detected if task == "pii" else inspection.hybrid.injection_detected
        source_status = inspection.hybrid.model_status

    outbound = None
    if decision.final_action != PolicyAction.BLOCK:
        outbound = _safe_provider_input(
            case.text, detections, pii_detected=pii_detected, policy_masked_text=decision.masked_text
        )
    # The evaluation records the text that would enter the provider, without sending it.
    return Observation(
        predicted, (time.perf_counter() - started) * 1000, call, source_status,
        outbound is None, outbound is not None, outbound is not None and outbound != case.text,
        outbound is not None and any(value.casefold() in outbound.casefold() for value in case.secrets),
    )


def _ratio(count: int, total: int) -> float | None:
    return count / total if total else None


def _metrics(cases: list[Case], rows: list[Observation]) -> dict | None:
    if not rows or any(row.predicted is None for row in rows):
        return None
    counts = Counter((case.positive, row.predicted) for case, row in zip(cases, rows))
    tp, fp, fn, tn = (counts[key] for key in ((True, True), (False, True), (True, False), (False, False)))
    has_negatives = bool(fp + tn)
    return {
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": _ratio(tp, tp + fp) if has_negatives else None,
        "recall": _ratio(tp, tp + fn),
        "f1": _ratio(2 * tp, 2 * tp + fp + fn) if has_negatives else None,
        "fpr": _ratio(fp, fp + tn), "fnr": _ratio(fn, fn + tp),
    }


def _summarize(cases: list[Case], rows: list[Observation]) -> dict:
    with_gold = [row for case, row in zip(cases, rows) if case.secrets]
    masked = [row for row in with_gold if row.masking_attempted]
    leaks = sum(row.leaked for row in with_gold)
    failed_masks = sum(row.leaked for row in masked)
    durations = [row.latency_ms for row in rows]
    calls = [row.local.latency_ms for row in rows if row.local.invoked]
    return {
        "detection": _metrics(cases, rows),
        "scored": sum(row.predicted is not None for row in rows),
        "model_status": dict(Counter(row.source_status for row in rows)),
        "local_status": dict(Counter(row.local.status for row in rows)),
        "blocked": sum(row.blocked for row in rows),
        "blocked_upstream_calls": sum(row.blocked and row.upstream_called for row in rows),
        "privacy": {
            "gold_positive_requests": len(with_gold), "masked_and_forwarded": len(masked),
            "masking_success_rate": _ratio(len(masked) - failed_masks, len(masked)),
            "masking_failure_rate": _ratio(failed_masks, len(masked)),
            "pii_transmission_rate": _ratio(leaks, len(with_gold)),
        } if with_gold else None,
        "latency_ms": {
            "mean": statistics.mean(durations), "p50": statistics.median(durations),
            "p95": statistics.quantiles(durations, n=100, method="inclusive")[94]
            if len(durations) > 1 else durations[0],
            "ollama_mean": statistics.mean(calls) if calls else None,
        },
        "ollama_calls": len(calls),
        "ollama_call_rate": _ratio(len(calls), len(rows)),
    }


async def _run(baseline_only: bool, limit_per_group: int | None) -> dict:
    inputs, digests = _inputs()
    local = get_ollama_settings()
    detection = replace(get_detection_settings(), detection_mode="hybrid")
    classifier = get_lightweight_classifier()
    client = OllamaClient(local)
    health = "not_requested" if baseline_only else await client.check_connection()
    warmup = await client.classify(WARMUP_TEXT) if health == "ready" else None
    if warmup is not None and warmup.status == "timeout":
        warmup = await client.classify(WARMUP_TEXT)
    run_local = warmup is not None and warmup.status == "completed"
    output = {
        "ollama_health": health, "ollama_model": client.model_name,
        "ollama_settings": {key: asdict(local)[key] for key in (
            "timeout_seconds", "max_input_length", "threshold_margin"
        )},
        "warmup": warmup.status if warmup is not None else None,
        "real_inference_verified": run_local,
        "limit_per_group": limit_per_group,
        "detection_settings": asdict(detection),
        "classifier_status": classifier.status().status,
        "classifier_sha256": {
            label: hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
            for label, path in (("classifier", classifier.classifier_path), ("vectorizer", classifier.vectorizer_path))
        },
        "dataset_sha256": digests,
        "platform": platform.platform(),
        "resources": None,
        "groups": [],
    }
    for (dataset, task), cases in inputs.items():
        available = len(cases)
        cases = _select_cases(cases, limit_per_group)
        print(f"{dataset} / {task} ({len(cases)} requests)", flush=True)
        group = {"dataset": dataset, "task": task, "requests": len(cases), "available": available, "modes": {}}
        observations = {}
        for mode in MODES:
            if not run_local and mode in {"Ollama Only", "Adaptive Hybrid"}:
                group["modes"][mode] = None
                continue
            print(f"  {mode}", flush=True)
            rows = []
            for index, case in enumerate(cases, start=1):
                rows.append(await _observe(case, task, mode, detection, local, classifier, client))
                if mode in {"Ollama Only", "Adaptive Hybrid"} and index % 25 == 0:
                    print(f"    {index}/{len(cases)}", flush=True)
            observations[mode] = rows
            group["modes"][mode] = _summarize(cases, rows)
        if run_local:
            common = [index for index, row in enumerate(observations["Ollama Only"]) if row.predicted is not None]
            if len(common) < len(cases):
                group["common_detection"] = {
                    "requests": len(common),
                    "modes": {
                        mode: _metrics([cases[index] for index in common], [rows[index] for index in common])
                        for mode, rows in observations.items()
                    },
                }
        output["groups"].append(group)
    return output


def _fmt(value) -> str:
    return "N/A" if value is None else f"{value:.3f}" if isinstance(value, float) else str(value)


def _report(result: dict) -> str:
    lines = [
        "# 적응형 탐지 비교 평가", "",
        f"- Ollama 모델 `{result['ollama_model']}`, 연결 상태 `{result['ollama_health']}`, "
        f"워밍업 `{result['warmup'] or 'Not measured'}`",
        "- 실제 Ollama 추론 " + ("Verified" if result["real_inference_verified"] else "Not verified"),
        f"- 경량 분류기 상태 `{result['classifier_status']}`, 운영 임계치 "
        f"`{result['detection_settings']['model_detector_threshold']}`, "
        f"라우팅 폭 `{result['ollama_settings']['threshold_margin']}`",
        "- 표시된 지연은 준비된 케이스의 프록시 입력 검사·정책·송신 준비 시간이다. "
        "HTTP 프록시·외부 생성·Validator Agent·로그 I/O는 포함하지 않는다.",
        "- Ollama 평균은 추론 API 호출이 시작된 요청의 모델 확인과 추론을 포함한다. "
        "CPU/RAM/VRAM 자동 수집은 N/A이며 별도 프로세스 표본은 "
        "[평가 실행 환경](../docs/ollama_adaptive_detection.md#평가-실행-환경)에 기록했다.",
        "- 탐지 표는 작업별 이진 플래그 비교다. 장애 차단은 별도 운영 결정이다. "
        "Ollama Only의 실패가 있으면 해당 코호트의 탐지 지표는 N/A이며 JSON에 채점 범위가 포함된다.",
        "- 양성만 포함한 Lakera 표에서 Precision·F1·FPR은 N/A다. "
        "외부 표는 저장소의 공개 데이터셋 부분집합에 한정된다.",
        "- 송신 검증은 정책과 송신 가드의 결과를 메모리에서 관찰했다. 실제 외부 네트워크 호출은 0건이다. "
        "합성 검증의 유출률은 정답 문자열이 포함된 양성 요청 대비 최소 하나가 송신될 비율이다. "
        "마스킹 성공률·실패율은 마스킹 후 송신된 정답 양성 요청 기준이다.",
        "- 내부 및 합성 결과는 회귀 확인용이다. 원문·정답 문자열·모델 자유 텍스트는 결과 파일에 저장하지 않는다.",
    ]
    if result["limit_per_group"] is not None:
        lines.append(
            f"- 재현 가능한 소규모 실행. 각 자료·작업에서 최대 {result['limit_per_group']}건, "
            "레이블별 비율을 보존하는 고정 시드(0) 표본을 사용했다."
        )
    for group in result["groups"]:
        metric_keys = ("precision", "recall", "f1", "tp", "fp", "fn", "tn", "fpr", "fnr")
        lines += [
            "", f"## {group['dataset']} / {group['task']} ({group['requests']}/{group['available']}건)", "",
            "| 방식 | 채점 수 | Precision | Recall | F1 | TP | FP | FN | TN | FPR | FNR |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for mode, row in group["modes"].items():
            metrics = (row or {}).get("detection") or {}
            values = [(row or {}).get("scored"), *(metrics.get(key) for key in metric_keys)]
            lines.append(f"| {mode} | " + " | ".join(map(_fmt, values)) + " |")
        if (common := group.get("common_detection")) is not None:
            lines += [
                "", f"Ollama Only 응답을 검증할 수 있었던 공통 부분집합 ({common['requests']}건)", "",
                "| 방식 | Precision | Recall | F1 | TP | FP | FN | TN | FPR | FNR |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
            for mode, metrics in common["modes"].items():
                values = [(metrics or {}).get(key) for key in metric_keys]
                lines.append(f"| {mode} | " + " | ".join(map(_fmt, values)) + " |")
        lines += [
            "", "| 방식 | 평균 ms | P50 ms | P95 ms | Ollama 평균 ms | Ollama 호출률 | 차단 | 차단 후 송신 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for mode, row in group["modes"].items():
            row = row or {}
            latency = row.get("latency_ms", {})
            values = [*(latency.get(key) for key in ("mean", "p50", "p95", "ollama_mean")),
                      row.get("ollama_call_rate"), row.get("blocked"), row.get("blocked_upstream_calls")]
            lines.append(f"| {mode} | " + " | ".join(map(_fmt, values)) + " |")
        if group["dataset"] == "synthetic_egress":
            lines += [
                "", "| 방식 | 정답 양성 | 마스킹 후 송신 | 마스킹 성공률 | 마스킹 실패율 | PII 송신률 |",
                "|---|---:|---:|---:|---:|---:|",
            ]
            for mode, row in group["modes"].items():
                privacy = (row or {}).get("privacy") or {}
                values = [privacy.get(key) for key in (
                    "gold_positive_requests", "masked_and_forwarded", "masking_success_rate",
                    "masking_failure_rate", "pii_transmission_rate",
                )]
                lines.append(f"| {mode} | " + " | ".join(map(_fmt, values)) + " |")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--baseline-only", action="store_true", help="Skip real Ollama modes")
    mode.add_argument("--health", action="store_true", help="Check the configured local model and exit")
    mode.add_argument("--warmup", action="store_true", help="Run one local inference with an example input")
    parser.add_argument("--limit-per-group", type=int, help="Use a reproducible stratified evaluation subset")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/ollama_adaptive_results")
    args = parser.parse_args()
    if args.limit_per_group is not None and args.limit_per_group < 2:
        parser.error("--limit-per-group must be at least 2")
    if args.health:
        health = asyncio.run(OllamaClient(get_ollama_settings()).check_connection())
        print(health)
        raise SystemExit(0 if health == "ready" else 1)
    if args.warmup:
        call = asyncio.run(OllamaClient(get_ollama_settings()).classify(WARMUP_TEXT))
        print(f"{call.status} ({_fmt(call.latency_ms)} ms)")
        raise SystemExit(0 if call.status == "completed" else 1)
    result = asyncio.run(_run(args.baseline_only, args.limit_per_group))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix(".json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.output.with_suffix(".md").write_text(_report(result), encoding="utf-8")
    if not args.baseline_only and result["warmup"] != "completed":
        raise SystemExit("Ollama was not verified. Baseline results were saved.")


if __name__ == "__main__":
    main()
