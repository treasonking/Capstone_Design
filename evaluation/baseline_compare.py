from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from backend.app.config import DetectionSettings
from backend.app.detection.hybrid_detector import detect_hybrid
from backend.app.detection.injection_detector import detect_injection
from backend.app.detection.lightweight_classifier import (
    LightweightClassifier,
    LightweightModelStatus,
    LightweightPrediction,
    get_lightweight_classifier,
)
from backend.app.detection.models import DetectorType


PROJECT_SCOPE = (
    "본 프로젝트는 범용 Prompt Injection 탐지기가 아니라, 한국어 공공기관·사내망 환경에서 "
    "발생할 수 있는 개인정보 유출 및 정책 우회형 Prompt Injection을 우선 방어 대상으로 "
    "설계한 LLM 보안 프록시이다."
)
EXTERNAL_RECALL_NOTE = (
    "외부 영어 데이터셋에서 낮은 Recall이 측정된 것은 현재 탐지 정책과 학습 데이터가 "
    "한국어 공공기관 시나리오에 집중되어 있기 때문이다. 이 결과는 시스템 실패로 숨기기보다, "
    "범용 환경 확장을 위한 개선 지점으로 해석한다."
)
DEFAULT_INTERNAL_DATASETS = [
    Path("evaluation/sample_dataset.json"),
    Path("evaluation/datasets/prompt_injection_english_cases.json"),
    Path("evaluation/datasets/prompt_injection_mixed_cases.json"),
]


@dataclass(frozen=True, slots=True)
class EvalSample:
    id: str
    dataset_name: str
    text: str
    expected_injection: bool


@dataclass(frozen=True, slots=True)
class DatasetBundle:
    name: str
    samples: list[EvalSample]
    status: str = "loaded"
    note: str = ""


Predictor = Callable[[str], bool]


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _metric(tp: int, fp: int, fn: int, tn: int) -> dict[str, float | int]:
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def _na_result(
    dataset_name: str,
    mode: str,
    model_status: str,
) -> dict[str, Any]:
    return {
        "dataset_name": dataset_name,
        "mode": mode,
        "precision": None,
        "recall": None,
        "f1": None,
        "tp": None,
        "fp": None,
        "fn": None,
        "tn": None,
        "latency_ms_avg": None,
        "model_status": model_status,
    }


def _expected_from_row(row: dict[str, Any]) -> bool:
    expected_label = str(row.get("expected_label", "")).strip().lower()
    if expected_label in {"injection", "prompt_injection", "attack"}:
        return True
    if expected_label in {"safe", "allow", "benign"}:
        return False

    expected_action = str(row.get("expected_action", "")).strip().upper()
    if expected_action in {"BLOCK", "WARN"}:
        return True
    if expected_action == "ALLOW":
        return False

    labels = row.get("labels", [])
    return any(str(label).startswith("INJ_") for label in labels)


def _is_prompt_injection_row(row: dict[str, Any]) -> bool:
    task = str(row.get("task", "")).strip().lower()
    if task in {"injection", "prompt_injection", "safe"}:
        return True
    return any(key in row for key in ("expected_label", "expected_action", "expected_reason"))


def _load_internal_samples(paths: list[Path]) -> DatasetBundle:
    samples: list[EvalSample] = []
    missing: list[str] = []

    for path in paths:
        if not path.exists():
            missing.append(str(path))
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        for row in rows:
            if not isinstance(row, dict) or not _is_prompt_injection_row(row):
                continue
            samples.append(
                EvalSample(
                    id=str(row.get("id", f"internal-{len(samples):04d}")),
                    dataset_name="internal",
                    text=str(row.get("text", "")),
                    expected_injection=_expected_from_row(row),
                )
            )

    note = f"Missing optional dataset files: {', '.join(missing)}" if missing else ""
    return DatasetBundle(name="internal", samples=samples, note=note)


def _load_deepset_samples(max_samples: int) -> DatasetBundle:
    if max_samples == 0:
        return DatasetBundle(
            name="deepset",
            samples=[],
            status="skipped",
            note="Skipped by --max-deepset-samples 0.",
        )

    try:
        from evaluation.external_datasets import load_deepset_prompt_injections

        external_samples = load_deepset_prompt_injections()
    except Exception as exc:
        return DatasetBundle(
            name="deepset",
            samples=[],
            status="unavailable",
            note=f"{exc.__class__.__name__}: {exc}",
        )

    if max_samples > 0:
        external_samples = external_samples[:max_samples]

    samples = [
        EvalSample(
            id=sample.id,
            dataset_name="deepset",
            text=sample.text,
            expected_injection=sample.expected_injection,
        )
        for sample in external_samples
    ]
    return DatasetBundle(name="deepset", samples=samples)


def _is_model_injection_prediction(prediction: LightweightPrediction) -> bool:
    if not prediction.detected:
        return False
    reason = str(prediction.reason_code or "").upper()
    label = prediction.label.upper()
    return "INJECTION" in reason or "INJ" in label or "PROMPT" in label or "JAILBREAK" in label


def _rule_only(text: str) -> bool:
    return bool(detect_injection(text))


def _model_only(classifier: LightweightClassifier) -> Predictor:
    def predict(text: str) -> bool:
        return _is_model_injection_prediction(classifier.classify(text))

    return predict


def _hybrid(text: str, settings: DetectionSettings) -> bool:
    result = detect_hybrid(text, settings=settings)
    return any(item.detector_type == DetectorType.INJECTION for item in result.detections)


def _evaluate(
    *,
    dataset_name: str,
    mode: str,
    samples: list[EvalSample],
    predictor: Predictor,
    model_status: str,
) -> dict[str, Any]:
    tp = fp = fn = tn = 0
    latencies: list[float] = []

    for sample in samples:
        started = time.perf_counter()
        predicted = predictor(sample.text)
        latencies.append((time.perf_counter() - started) * 1000)

        if predicted and sample.expected_injection:
            tp += 1
        elif predicted and not sample.expected_injection:
            fp += 1
        elif not predicted and sample.expected_injection:
            fn += 1
        else:
            tn += 1

    metric = _metric(tp, fp, fn, tn)
    return {
        "dataset_name": dataset_name,
        "mode": mode,
        **metric,
        "latency_ms_avg": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
        "model_status": model_status,
    }


def _mode_rows_for_dataset(
    dataset: DatasetBundle,
    classifier: LightweightClassifier,
    classifier_status: LightweightModelStatus,
    threshold: float,
) -> list[dict[str, Any]]:
    if dataset.status != "loaded" or not dataset.samples:
        status = dataset.status if dataset.status != "loaded" else "empty"
        return [
            _na_result(dataset.name, "Rule Only", status),
            _na_result(dataset.name, "Model Only", status),
            _na_result(dataset.name, "Hybrid", status),
        ]

    rows = [
        _evaluate(
            dataset_name=dataset.name,
            mode="Rule Only",
            samples=dataset.samples,
            predictor=_rule_only,
            model_status="disabled",
        )
    ]

    classifier.threshold = threshold
    if classifier_status.enabled:
        rows.append(
            _evaluate(
                dataset_name=dataset.name,
                mode="Model Only",
                samples=dataset.samples,
                predictor=_model_only(classifier),
                model_status=classifier_status.status,
            )
        )
    else:
        rows.append(_na_result(dataset.name, "Model Only", classifier_status.status))

    hybrid_mode = "Hybrid" if classifier_status.enabled else "Hybrid(fallback)"
    hybrid_settings = DetectionSettings(
        enable_model_detector=True,
        detection_mode="hybrid",
        model_detector_threshold=threshold,
        model_detector_fail_mode="warn",
    )
    rows.append(
        _evaluate(
            dataset_name=dataset.name,
            mode=hybrid_mode,
            samples=dataset.samples,
            predictor=lambda text: _hybrid(text, hybrid_settings),
            model_status=classifier_status.status,
        )
    )
    return rows


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _render_markdown(
    *,
    datasets: list[DatasetBundle],
    rows: list[dict[str, Any]],
    classifier_status: LightweightModelStatus,
) -> str:
    lines = [
        "# Rule Only vs Hybrid Baseline Comparison",
        "",
        PROJECT_SCOPE,
        "",
        EXTERNAL_RECALL_NOTE,
        "",
        "## Lightweight Classifier Status",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| model_status | {classifier_status.status} |",
        f"| enabled | {str(classifier_status.enabled).lower()} |",
        f"| vectorizer_path | `{classifier_status.vectorizer_path}` |",
        f"| classifier_path | `{classifier_status.classifier_path}` |",
        f"| note | {classifier_status.note} |",
        "",
        "Lightweight classifier artifact가 존재하지 않는 경우 시스템은 실행 중단 대신 rule-based fallback으로 동작한다. 이는 데모 안정성을 위한 설계이나, Hybrid 성능 평가에서는 `model_status`를 `artifact_missing`으로 분리 표시한다. 따라서 fallback 상태의 결과를 완전한 Hybrid 성능으로 해석하지 않는다.",
        "",
        "## Datasets",
        "",
        "| Dataset | Samples | Status | Note |",
        "|---|---:|---|---|",
    ]

    for dataset in datasets:
        note = dataset.note.replace("|", "\\|") if dataset.note else "-"
        lines.append(f"| {dataset.name} | {len(dataset.samples)} | {dataset.status} | {note} |")

    lines.extend(
        [
            "",
            "## Results",
            "",
            "| Dataset | Mode | Precision | Recall | F1 | TP | FP | FN | Avg Latency(ms) | Model Status |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )

    for row in rows:
        lines.append(
            f"| {row['dataset_name']} "
            f"| {row['mode']} "
            f"| {_fmt(row['precision'])} "
            f"| {_fmt(row['recall'])} "
            f"| {_fmt(row['f1'])} "
            f"| {_fmt(row['tp'])} "
            f"| {_fmt(row['fp'])} "
            f"| {_fmt(row['fn'])} "
            f"| {_fmt(row['latency_ms_avg'])} "
            f"| {row['model_status']} |"
        )

    lines.extend(
        [
            "",
            "## Reading Guide",
            "",
            "- `Rule Only`는 regex/rule 기반 Prompt Injection 탐지만 사용한다.",
            "- `Model Only`는 `models/lightweight/vectorizer.joblib`, `models/lightweight/classifier.joblib`가 모두 로드된 경우에만 측정한다. artifact가 없으면 `N/A`로 표시한다.",
            "- `Hybrid(fallback)`은 경량 분류 artifact가 없거나 사용할 수 없어 rule 기반 fallback 경로로 평가된 상태이다. 이 값은 완전한 Hybrid 성능으로 과장하지 않는다.",
            "- 외부 영어 데이터셋 결과는 한국어 공공기관·사내망 특화 정책의 일반화 한계를 확인하기 위한 보조 근거로 사용한다.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_outputs(
    *,
    datasets: list[DatasetBundle],
    rows: list[dict[str, Any]],
    classifier_status: LightweightModelStatus,
    report_path: Path,
    results_path: Path,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _render_markdown(
            datasets=datasets,
            rows=rows,
            classifier_status=classifier_status,
        ),
        encoding="utf-8",
    )
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scope": PROJECT_SCOPE,
        "external_recall_note": EXTERNAL_RECALL_NOTE,
        "classifier_status": {
            "enabled": classifier_status.enabled,
            "status": classifier_status.status,
            "note": classifier_status.note,
            "vectorizer_path": str(classifier_status.vectorizer_path),
            "classifier_path": str(classifier_status.classifier_path),
        },
        "datasets": [
            {
                "name": dataset.name,
                "samples": len(dataset.samples),
                "status": dataset.status,
                "note": dataset.note,
            }
            for dataset in datasets
        ],
        "results": rows,
    }
    results_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Rule Only, Lightweight Model Only, and Hybrid Prompt Injection detection."
    )
    parser.add_argument(
        "--internal-dataset",
        action="append",
        default=[],
        help="Internal JSON dataset path. Can be provided multiple times.",
    )
    parser.add_argument(
        "--max-deepset-samples",
        type=int,
        default=662,
        help="Maximum deepset samples to evaluate. Use 0 to skip deepset.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.7,
        help="Lightweight classifier threshold.",
    )
    parser.add_argument(
        "--report",
        default="reports/baseline_compare_report.md",
        help="Output markdown report path.",
    )
    parser.add_argument(
        "--results",
        default="reports/baseline_compare_results.json",
        help="Output JSON results path.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    internal_paths = [Path(path) for path in args.internal_dataset] or DEFAULT_INTERNAL_DATASETS
    datasets = [
        _load_internal_samples(internal_paths),
        _load_deepset_samples(args.max_deepset_samples),
    ]

    classifier = get_lightweight_classifier()
    classifier_status = classifier.status()
    rows: list[dict[str, Any]] = []
    for dataset in datasets:
        rows.extend(
            _mode_rows_for_dataset(
                dataset,
                classifier,
                classifier_status,
                args.threshold,
            )
        )

    _write_outputs(
        datasets=datasets,
        rows=rows,
        classifier_status=classifier_status,
        report_path=Path(args.report),
        results_path=Path(args.results),
    )
    print(f"Baseline comparison saved to: {args.report}")
    print(f"Baseline comparison JSON saved to: {args.results}")


if __name__ == "__main__":
    main()
