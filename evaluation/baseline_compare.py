from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from backend.app.detection.hybrid_detector import detect_hybrid
from backend.app.detection.injection_detector import detect_injection
from backend.app.detection.lightweight_classifier import (
    LightweightModelStatus,
    get_lightweight_classifier,
)
from backend.app.detection.models import DetectionResult, DetectorType
from backend.app.detection.pii_detector import detect_pii


DetectorFunc = Callable[[str], list[DetectionResult]]


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _metric(tp: int, fp: int, fn: int, tn: int) -> dict[str, float | int]:
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    accuracy = _safe_div(tp + tn, tp + fp + fn + tn)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
    }


def _na_metric() -> dict[str, str]:
    return {
        "precision": "N/A",
        "recall": "N/A",
        "f1": "N/A",
        "accuracy": "N/A",
    }


def _expected_positive(row: dict[str, Any]) -> bool:
    return bool(row.get("labels", []))


def _detector_type(task: str) -> DetectorType:
    return DetectorType.PII if task == "pii" else DetectorType.INJECTION


def _evaluate_rows(
    rows: list[dict[str, Any]],
    detector: DetectorFunc,
) -> dict[str, float | int]:
    tp = fp = fn = tn = 0
    for row in rows:
        predicted_positive = bool(detector(str(row.get("text", ""))))
        expected_positive = _expected_positive(row)
        if predicted_positive and expected_positive:
            tp += 1
        elif predicted_positive and not expected_positive:
            fp += 1
        elif not predicted_positive and expected_positive:
            fn += 1
        else:
            tn += 1
    return _metric(tp, fp, fn, tn)


def _regex_only(text: str) -> list[DetectionResult]:
    return detect_pii(text)


def _rule_only(text: str) -> list[DetectionResult]:
    return detect_injection(text)


def _model_only(text: str, task: str) -> list[DetectionResult]:
    summary = detect_hybrid(text)
    target_type = _detector_type(task)
    return [
        item
        for item in summary.detections
        if item.category.startswith("MODEL_")
        and item.detector_type == target_type
    ]


def _hybrid(text: str, task: str) -> list[DetectionResult]:
    summary = detect_hybrid(text)
    target_type = _detector_type(task)
    return [
        item
        for item in summary.detections
        if item.detector_type == target_type
    ]


def _format_metric(value: float | int | str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return str(value)
    return f"{value:.3f}"


def _status_note(status: LightweightModelStatus) -> str:
    if status.enabled:
        return (
            "현재 모델 artifact가 로드되어 Lightweight Classification Layer와 "
            "Full Multi-layered Pipeline 평가에 경량 분류 결과가 반영된다."
        )
    if status.status == "artifact_missing":
        return (
            "경량 분류 계층 artifact가 없어 Lightweight Classification Layer only는 "
            "unavailable로 표시되고 Full Multi-layered Pipeline은 regex+heuristic fallback으로 동작한다."
        )
    if status.status == "dependency_missing":
        return (
            "경량 분류 계층 의존성이 없어 Lightweight Classification Layer only는 "
            "unavailable로 표시되고 Full Multi-layered Pipeline은 regex+heuristic fallback으로 동작한다."
        )
    if status.status == "disabled":
        return (
            "구성에서 경량 분류 계층이 비활성화되어 Lightweight Classification Layer only는 "
            "unavailable로 표시되고 Full Multi-layered Pipeline은 regex+heuristic fallback으로 동작한다."
        )
    return (
        "경량 분류 artifact 로드에 실패해 Lightweight Classification Layer only는 "
        "unavailable로 표시되고 Full Multi-layered Pipeline은 regex+heuristic fallback으로 동작한다."
    )


def _render_report(
    *,
    dataset_path: str,
    dataset_size: int,
    classifier_status: LightweightModelStatus,
    regex_pii: dict[str, float | int],
    rule_injection: dict[str, float | int],
    model_pii: dict[str, float | int] | dict[str, str],
    model_injection: dict[str, float | int] | dict[str, str],
    hybrid_pii: dict[str, float | int],
    hybrid_injection: dict[str, float | int],
    output_path: Path,
) -> Path:
    enabled_text = "true" if classifier_status.enabled else "false"
    model_only_status = "available" if classifier_status.enabled else "unavailable"
    pipeline_status = "available" if classifier_status.enabled else "regex+heuristic fallback"
    rows = [
        ("A. Regex Pattern Layer only", "pii", regex_pii, "available"),
        (
            "B. Heuristic Rule Layer only",
            "injection",
            rule_injection,
            "available",
        ),
        (
            "C. Lightweight Classification Layer only",
            "pii",
            model_pii,
            model_only_status,
        ),
        (
            "C. Lightweight Classification Layer only",
            "injection",
            model_injection,
            model_only_status,
        ),
        (
            "D. Regex Pattern Layer + Heuristic Rule Layer",
            "pii",
            regex_pii,
            "available",
        ),
        (
            "D. Regex Pattern Layer + Heuristic Rule Layer",
            "injection",
            rule_injection,
            "available",
        ),
        (
            "E. Full Multi-layered Pipeline",
            "pii",
            hybrid_pii,
            pipeline_status,
        ),
        (
            "E. Full Multi-layered Pipeline",
            "injection",
            hybrid_injection,
            pipeline_status,
        ),
    ]

    lines = [
        "# Multi-layered Detection Ablation Report",
        "",
        "> 이 리포트는 동일한 내부 회귀 데이터셋에서 다층형 탐지 파이프라인의 계층별 기여도를 비교한 요약이다. 현재 보고서는 경량 분류 계층 artifact 또는 의존성이 없는 환경에서 실행되었기 때문에 Lightweight Classification Layer only 결과는 `N/A`로 표시된다. 따라서 이 보고서는 최종 계층별 성능 비교가 아니라, 현재 MVP가 경량 분류 계층 비활성화 상황에서도 Regex Pattern Layer와 Heuristic Rule Layer를 통해 안정적으로 동작하는지 확인하는 중간 보고서이다.",
        "",
        "## Dataset",
        f"- Path: `{dataset_path}`",
        f"- Size: {dataset_size}",
        "",
        "## Ablation Groups",
        "",
        "| Group | Configuration | Purpose |",
        "|---|---|---|",
        "| A | Regex Pattern Layer only | 정규식 계층이 정형 PII 탐지에서 얼마나 효과적인지 확인한다. |",
        "| B | Heuristic Rule Layer only | 휴리스틱 규칙 계층이 프롬프트 인젝션 탐지 성능에 얼마나 기여하는지 확인한다. |",
        "| C | Lightweight Classification Layer only | 경량 분류 계층이 비정형 공격 탐지에 기여하는지 확인한다. |",
        "| D | Regex Pattern Layer + Heuristic Rule Layer | 정형 PII와 명시적 인젝션 단서 결합 시 탐지 안정성을 확인한다. |",
        "| E | Full Multi-layered Detection Pipeline | 최종 다층형 구조가 단일 계층 구조보다 Recall과 안정성을 높이는지 확인한다. |",
        "",
        "향후 최종 비교에서는 경량 분류 계층 artifact를 생성한 뒤 다음 실험군을 모두 비교한다.",
        "",
        "1. A. Regex Pattern Layer only",
        "2. B. Heuristic Rule Layer only",
        "3. C. Lightweight Classification Layer only",
        "4. D. Regex Pattern Layer + Heuristic Rule Layer",
        "5. E. Full Multi-layered Detection Pipeline",
        "",
        "## Lightweight Classification Layer Status",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Lightweight classification layer enabled | {enabled_text} |",
        f"| Lightweight classification layer status | {classifier_status.status} |",
        f"| Interpretation | {_status_note(classifier_status)} |",
        "",
        "## Results",
        "",
        "| Mode | Task | Precision | Recall | F1 | Accuracy | Status |",
        "|---|---|---:|---:|---:|---:|---|",
    ]

    for mode, task, metric, status in rows:
        lines.append(
            f"| {mode} | {task} | "
            f"{_format_metric(metric['precision'])} | "
            f"{_format_metric(metric['recall'])} | "
            f"{_format_metric(metric['f1'])} | "
            f"{_format_metric(metric['accuracy'])} | "
            f"{status} |"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare multi-layered detection pipeline ablation groups."
    )
    parser.add_argument(
        "--dataset",
        default="evaluation/sample_dataset.json",
        help="Path to JSON dataset.",
    )
    parser.add_argument(
        "--report",
        default="reports/baseline_compare_report.md",
        help="Output markdown report path.",
    )
    args = parser.parse_args()

    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    pii_rows = [row for row in dataset if row.get("task") == "pii"]
    injection_rows = [row for row in dataset if row.get("task") == "injection"]
    classifier_status = get_lightweight_classifier().status()

    regex_pii = _evaluate_rows(pii_rows, _regex_only)
    rule_injection = _evaluate_rows(injection_rows, _rule_only)
    hybrid_pii = _evaluate_rows(pii_rows, lambda text: _hybrid(text, "pii"))
    hybrid_injection = _evaluate_rows(
        injection_rows,
        lambda text: _hybrid(text, "injection"),
    )

    if classifier_status.enabled:
        model_pii: dict[str, float | int] | dict[str, str] = _evaluate_rows(
            pii_rows,
            lambda text: _model_only(text, "pii"),
        )
        model_injection: dict[str, float | int] | dict[str, str] = _evaluate_rows(
            injection_rows,
            lambda text: _model_only(text, "injection"),
        )
    else:
        model_pii = _na_metric()
        model_injection = _na_metric()

    output_path = _render_report(
        dataset_path=args.dataset,
        dataset_size=len(dataset),
        classifier_status=classifier_status,
        regex_pii=regex_pii,
        rule_injection=rule_injection,
        model_pii=model_pii,
        model_injection=model_injection,
        hybrid_pii=hybrid_pii,
        hybrid_injection=hybrid_injection,
        output_path=Path(args.report),
    )
    print(f"Baseline comparison saved to: {output_path}")


if __name__ == "__main__":
    main()
