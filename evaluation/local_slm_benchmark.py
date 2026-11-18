from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import os
import platform
import re
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.schemas.proxy import ProxyRequest
from backend.app.services.proxy_service import process_proxy_chat


DEFAULT_JSON_PATH = Path("reports/local_slm_benchmark_results.json")
DEFAULT_CSV_PATH = Path("reports/local_slm_benchmark_results.csv")
CASES: tuple[dict[str, Any], ...] = (
    {"id": "ko_capital", "prompt": "대한민국의 수도를 한 단어로 답해줘.", "must_include": ["서울"]},
    {"id": "ko_arithmetic", "prompt": "17 곱하기 23의 결과만 답해줘.", "must_include": ["391"]},
    {
        "id": "ko_rag_explanation",
        "prompt": "RAG의 역할을 한국어 한 문장으로 설명해줘. '검색'과 '문서'를 포함해.",
        "must_include": ["검색", "문서"],
    },
    {
        "id": "ko_fact_summary",
        "prompt": (
            "다음 사실만 한 문장으로 요약해줘: 접수 창구는 월요일부터 금요일까지 운영한다. "
            "운영 시간은 오전 9시부터 오후 6시까지다."
        ),
        "must_include": ["월요일", "금요일", "9시", "6시"],
    },
)


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def _quality_pass(content: str | None, required: list[str]) -> bool:
    if not content:
        return False
    normalized = re.sub(r"\s+", "", content).casefold()
    return all(re.sub(r"\s+", "", item).casefold() in normalized for item in required)


async def _measure_model(model: str, *, iterations: int, warmup: int) -> list[dict[str, Any]]:
    os.environ["LLM_PROVIDER"] = "ollama"
    os.environ["OLLAMA_MODEL"] = model

    for _ in range(warmup):
        await process_proxy_chat(ProxyRequest(message=CASES[0]["prompt"]))

    measurements: list[dict[str, Any]] = []
    for iteration in range(1, iterations + 1):
        for case in CASES:
            started = time.perf_counter()
            result = await process_proxy_chat(ProxyRequest(message=case["prompt"]))
            total_latency_ms = round((time.perf_counter() - started) * 1000, 2)
            audit = result.audit_summary
            measurements.append(
                {
                    "model": model,
                    "case_id": case["id"],
                    "iteration": iteration,
                    "action": result.action,
                    "quality_pass": _quality_pass(result.content, case["must_include"]),
                    "upstream_latency_ms": audit.get("upstream_latency_ms"),
                    "proxy_total_latency_ms": total_latency_ms,
                    "error_type": audit.get("error_type"),
                }
            )
    return measurements


def _summarize(measurements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in measurements:
        grouped[item["model"]].append(item)

    summaries = []
    for model, items in sorted(grouped.items()):
        total = [item["proxy_total_latency_ms"] for item in items]
        upstream = [
            item["upstream_latency_ms"]
            for item in items
            if isinstance(item["upstream_latency_ms"], (int, float))
        ]
        quality_pass_count = sum(item["quality_pass"] for item in items)
        summaries.append(
            {
                "model": model,
                "sample_count": len(items),
                "quality_pass_count": quality_pass_count,
                "quality_pass_rate": round(quality_pass_count / len(items), 4) if items else 0.0,
                "error_count": sum(item["action"] == "ERROR" for item in items),
                "avg_upstream_latency_ms": round(mean(upstream), 2) if upstream else None,
                "p95_upstream_latency_ms": round(_p95(upstream), 2) if upstream else None,
                "avg_proxy_total_latency_ms": round(mean(total), 2) if total else None,
                "p95_proxy_total_latency_ms": round(_p95(total), 2) if total else None,
            }
        )
    return summaries


async def _run(models: list[str], *, iterations: int, warmup: int) -> dict[str, Any]:
    measurements: list[dict[str, Any]] = []
    for model in models:
        measurements.extend(await _measure_model(model, iterations=iterations, warmup=warmup))
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "provider": "ollama",
        "platform": platform.platform(),
        "processor": platform.processor() or None,
        "logical_cpu_count": os.cpu_count(),
        "warmup_iterations_per_model": warmup,
        "measured_iterations_per_case": iterations,
        "case_count": len(CASES),
        "cases": [{"id": case["id"], "must_include": case["must_include"]} for case in CASES],
        "summary": _summarize(measurements),
        "measurements": measurements,
        "limitations": [
            "Keyword checks are a small smoke-test signal, not a human quality evaluation.",
            "Latency depends on model load state, CPU/GPU, quantization, and Ollama configuration.",
            "GPU model and VRAM usage are not collected automatically.",
            "Only requests that pass the existing input policy reach the local model.",
        ],
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare local Ollama models through the existing security proxy."
    )
    parser.add_argument("--models", nargs="+", default=None, help="Ollama model names; defaults to OLLAMA_MODEL.")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--json", default=str(DEFAULT_JSON_PATH))
    parser.add_argument("--csv", default=str(DEFAULT_CSV_PATH))
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.iterations <= 0:
        raise ValueError("--iterations must be positive.")
    if args.warmup < 0:
        raise ValueError("--warmup must not be negative.")
    configured_model = os.getenv("OLLAMA_MODEL", "").strip()
    models = args.models or ([configured_model] if configured_model else [])
    if not models:
        raise ValueError("Set OLLAMA_MODEL or pass one or more --models.")
    if len(set(models)) != len(models):
        raise ValueError("Model names in --models must be unique.")

    result = asyncio.run(_run(models, iterations=args.iterations, warmup=args.warmup))
    json_path = Path(args.json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_path = Path(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["model", "case_id", "iteration", "action", "quality_pass", "upstream_latency_ms", "proxy_total_latency_ms", "error_type"]
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(result["measurements"])

    print(f"Local SLM benchmark JSON saved to: {json_path}")
    print(f"Local SLM benchmark CSV saved to: {csv_path}")
    for summary in result["summary"]:
        print(
            f"{summary['model']}: quality={summary['quality_pass_rate']:.1%}, "
            f"upstream_avg={summary['avg_upstream_latency_ms']} ms, "
            f"proxy_avg={summary['avg_proxy_total_latency_ms']} ms"
        )


if __name__ == "__main__":
    main()
