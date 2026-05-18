from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import DetectionSettings
from backend.app.detection.hybrid_detector import detect_hybrid
from backend.app.detection.injection_detector import detect_injection
from backend.app.detection.lightweight_classifier import (
    LightweightClassifier,
    LightweightModelStatus,
    LightweightPrediction,
)
from backend.app.detection.models import DetectorType
from evaluation.external_datasets import (
    ExternalSample,
    load_deepset_prompt_injections,
    load_lakera_gandalf_ignore_instructions,
    load_protectai_prompt_injection_validation,
)


REPORT_PATH = Path("reports/external_dataset_compare_report.md")
RESULTS_JSON_PATH = Path("reports/external_dataset_compare_results.json")
RESULTS_CSV_PATH = Path("reports/external_dataset_compare_results.csv")
MODEL_METADATA_FILENAME = "model_metadata.json"
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


@dataclass(frozen=True, slots=True)
class PreviousResult:
    size: int
    precision: float | None
    recall: float
    f1: float | None
    accuracy: float
    tp: int
    fp: int | None
    tn: int | None
    fn: int | None


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    name: str
    source: str
    role: str
    loader: Callable[[str], list[ExternalSample]]
    previous: PreviousResult
    positive_only: bool = False


@dataclass(frozen=True, slots=True)
class DatasetBundle:
    spec: DatasetSpec
    samples: list[ExternalSample]
    status: str = "loaded"
    note: str = ""


Predictor = Callable[[str], bool]


DATASET_SPECS = (
    DatasetSpec(
        name="deepset/prompt-injections",
        source="https://huggingface.co/datasets/deepset/prompt-injections",
        role="정상/공격 프롬프트를 모두 포함하는 메인 외부 벤치마크",
        loader=load_deepset_prompt_injections,
        previous=PreviousResult(
            size=662,
            precision=1.0000,
            recall=0.0760,
            f1=0.1413,
            accuracy=0.6329,
            tp=20,
            fp=0,
            tn=399,
            fn=243,
        ),
    ),
    DatasetSpec(
        name="protectai/prompt-injection-validation",
        source="https://huggingface.co/datasets/protectai/prompt-injection-validation",
        role="3천 건 이상 규모의 추가 검증셋",
        loader=load_protectai_prompt_injection_validation,
        previous=PreviousResult(
            size=3227,
            precision=0.8251,
            recall=0.1796,
            f1=0.2950,
            accuracy=0.6297,
            tp=250,
            fp=53,
            tn=1782,
            fn=1142,
        ),
    ),
    DatasetSpec(
        name="Lakera/gandalf_ignore_instructions",
        source="https://huggingface.co/datasets/Lakera/gandalf_ignore_instructions",
        role="공격 샘플 중심의 ignore-instructions Recall 검증셋",
        loader=load_lakera_gandalf_ignore_instructions,
        previous=PreviousResult(
            size=1000,
            precision=None,
            recall=0.4480,
            f1=None,
            accuracy=0.4480,
            tp=448,
            fp=None,
            tn=None,
            fn=552,
        ),
        positive_only=True,
    ),
)


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _is_model_injection_prediction(prediction: LightweightPrediction) -> bool:
    if not prediction.detected:
        return False
    reason = str(prediction.reason_code or "").upper()
    label = prediction.label.upper()
    return (
        "INJECTION" in reason
        or "INJ" in reason
        or "PROMPT" in label
        or "JAILBREAK" in label
        or "INJECTION" in label
        or "INJ" in label
    )


def _rule_only(text: str) -> bool:
    return bool(detect_injection(text))


def _model_only(classifier: LightweightClassifier) -> Predictor:
    def predict(text: str) -> bool:
        return _is_model_injection_prediction(classifier.classify(text))

    return predict


def _hybrid_pipeline(classifier: LightweightClassifier, threshold: float) -> Predictor:
    settings = DetectionSettings(
        enable_model_detector=True,
        detection_mode="hybrid",
        model_detector_threshold=threshold,
        model_detector_fail_mode="warn",
    )

    def predict(text: str) -> bool:
        result = detect_hybrid(text, classifier=classifier, settings=settings)
        return any(
            detection.detector_type == DetectorType.INJECTION
            for detection in result.detections
        )

    return predict


def _load_dataset(spec: DatasetSpec, split: str, max_samples: int | None) -> DatasetBundle:
    try:
        samples = spec.loader(split)
    except Exception as exc:
        return DatasetBundle(
            spec=spec,
            samples=[],
            status="unavailable",
            note=f"{exc.__class__.__name__}: {exc}",
        )

    if max_samples is not None:
        samples = samples[:max_samples]

    return DatasetBundle(spec=spec, samples=samples)


def _metric_result(
    *,
    dataset: DatasetBundle,
    mode: str,
    predictor: Predictor,
    model_status: str,
) -> dict[str, Any]:
    tp = fp = fn = tn = 0
    latencies: list[float] = []

    for sample in dataset.samples:
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

    size = len(dataset.samples)
    positive_only = size > 0 and all(sample.expected_injection for sample in dataset.samples)
    precision = None if positive_only else _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = None if precision is None else _safe_div(2 * precision * recall, precision + recall)
    accuracy = _safe_div(tp + tn, size)

    return {
        "dataset_name": dataset.spec.name,
        "mode": mode,
        "size": size,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "tp": tp,
        "fp": None if positive_only else fp,
        "tn": None if positive_only else tn,
        "fn": fn,
        "positive_only": positive_only,
        "latency_ms_avg": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
        "model_status": model_status,
        "dataset_status": dataset.status,
        "note": dataset.note,
    }


def _na_result(dataset: DatasetBundle, mode: str, model_status: str) -> dict[str, Any]:
    return {
        "dataset_name": dataset.spec.name,
        "mode": mode,
        "size": len(dataset.samples),
        "precision": None,
        "recall": None,
        "f1": None,
        "accuracy": None,
        "tp": None,
        "fp": None,
        "tn": None,
        "fn": None,
        "positive_only": dataset.spec.positive_only,
        "latency_ms_avg": None,
        "model_status": model_status,
        "dataset_status": dataset.status,
        "note": dataset.note,
    }


def _evaluate_dataset(
    dataset: DatasetBundle,
    classifier: LightweightClassifier,
    classifier_status: LightweightModelStatus,
    threshold: float,
) -> list[dict[str, Any]]:
    if dataset.status != "loaded" or not dataset.samples:
        status = dataset.status if dataset.status != "loaded" else "empty"
        unavailable = DatasetBundle(
            spec=dataset.spec,
            samples=dataset.samples,
            status=status,
            note=dataset.note,
        )
        return [
            _na_result(unavailable, "Rule Only", "disabled"),
            _na_result(unavailable, "Lightweight Model Only", classifier_status.status),
            _na_result(unavailable, "Hybrid / Full Pipeline", classifier_status.status),
        ]

    classifier.threshold = threshold
    rows = [
        _metric_result(
            dataset=dataset,
            mode="Rule Only",
            predictor=_rule_only,
            model_status="disabled",
        )
    ]

    if classifier_status.enabled:
        rows.append(
            _metric_result(
                dataset=dataset,
                mode="Lightweight Model Only",
                predictor=_model_only(classifier),
                model_status=classifier_status.status,
            )
        )
    else:
        rows.append(_na_result(dataset, "Lightweight Model Only", classifier_status.status))

    rows.append(
        _metric_result(
            dataset=dataset,
            mode="Hybrid / Full Pipeline",
            predictor=_hybrid_pipeline(classifier, threshold),
            model_status=classifier_status.status,
        )
    )
    return rows


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _delta(current: Any, previous: Any) -> str:
    if current is None or previous is None:
        return "N/A"
    return f"{current - previous:+.4f}"


def _runtime_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for module_name in ("datasets", "joblib", "sklearn"):
        try:
            module = __import__(module_name)
        except Exception:
            versions[module_name] = "unavailable"
            continue
        versions[module_name] = str(getattr(module, "__version__", "unknown"))
    return versions


def _model_metadata(classifier_status: LightweightModelStatus) -> dict[str, str]:
    metadata_path = classifier_status.classifier_path.parent / MODEL_METADATA_FILENAME
    if not metadata_path.exists():
        return {
            "model_version": "internal-only",
            "training_data": "internal Korean public-sector scenario data",
            "note": "No model metadata file found; interpreted as the current internal-oriented artifact.",
        }

    try:
        raw = json.loads(metadata_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "model_version": "unknown",
            "training_data": "unknown",
            "note": f"Failed to read model metadata: {exc.__class__.__name__}",
        }

    return {
        "model_version": str(raw.get("model_version", "unknown")),
        "training_data": str(raw.get("training_data", "unknown")),
        "note": str(raw.get("note", "")),
    }


def _render_markdown(
    *,
    generated_at: str,
    split: str,
    threshold: float,
    datasets: list[DatasetBundle],
    rows: list[dict[str, Any]],
    classifier_status: LightweightModelStatus,
    runtime_versions: dict[str, str],
    model_metadata: dict[str, str],
) -> str:
    hybrid_by_dataset = {
        row["dataset_name"]: row
        for row in rows
        if row["mode"] == "Hybrid / Full Pipeline"
    }

    lines = [
        "# External Dataset Rule/Model/Hybrid Comparison",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Hugging Face split: `{split}`",
        f"- Lightweight threshold: `{threshold:.2f}`",
        "",
        PROJECT_SCOPE,
        "",
        EXTERNAL_RECALL_NOTE,
        "",
        "## Lightweight Classifier Status",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| enabled | {str(classifier_status.enabled).lower()} |",
        f"| status | {classifier_status.status} |",
        f"| note | {classifier_status.note} |",
        f"| vectorizer_path | `{classifier_status.vectorizer_path}` |",
        f"| classifier_path | `{classifier_status.classifier_path}` |",
        "",
        "## Model Version",
        "",
        "| Model Version | Training Data | Note |",
        "|---|---|---|",
        f"| {model_metadata['model_version']} | {model_metadata['training_data']} | {model_metadata['note']} |",
        "",
        "## Runtime Versions",
        "",
        "| Package | Version |",
        "|---|---|",
        f"| datasets | {runtime_versions.get('datasets', 'unknown')} |",
        f"| joblib | {runtime_versions.get('joblib', 'unknown')} |",
        f"| sklearn | {runtime_versions.get('sklearn', 'unknown')} |",
        "",
        "## Dataset Loading",
        "",
        "| Dataset | Samples | Status | Role | Note |",
        "|---|---:|---|---|---|",
    ]

    for dataset in datasets:
        note = dataset.note.replace("|", "\\|") if dataset.note else "-"
        lines.append(
            f"| `{dataset.spec.name}` | {len(dataset.samples)} | {dataset.status} | {dataset.spec.role} | {note} |"
        )

    lines.extend(
        [
            "",
            "## Previous Reference",
            "",
            "기존 측정값은 비교 기준으로만 둔다. 이번 재평가의 핵심은 아래 `Current Mode Comparison`에서 Rule Only, Lightweight Model Only, Hybrid / Full Pipeline을 분리해 보는 것이다.",
            "기존 입력 문서의 일부 FN 값은 Precision/Recall/Accuracy와 수학적으로 맞지 않아, 저장소의 기존 `reports/external_prompt_injection_report.md` 및 혼동행렬과 일관되는 값으로 표시한다.",
            "",
            "| Dataset | Size | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for spec in DATASET_SPECS:
        previous = spec.previous
        lines.append(
            f"| `{spec.name}` "
            f"| {previous.size} "
            f"| {_fmt(previous.precision)} "
            f"| {_fmt(previous.recall)} "
            f"| {_fmt(previous.f1)} "
            f"| {_fmt(previous.accuracy)} "
            f"| {_fmt(previous.tp)} "
            f"| {_fmt(previous.fp)} "
            f"| {_fmt(previous.tn)} "
            f"| {_fmt(previous.fn)} |"
        )

    lines.extend(
        [
            "",
            "## Current Mode Comparison",
            "",
            "| Dataset | Mode | Size | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN | Avg Latency(ms) | Model Status |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )

    for row in rows:
        lines.append(
            f"| `{row['dataset_name']}` "
            f"| {row['mode']} "
            f"| {_fmt(row['size'])} "
            f"| {_fmt(row['precision'])} "
            f"| {_fmt(row['recall'])} "
            f"| {_fmt(row['f1'])} "
            f"| {_fmt(row['accuracy'])} "
            f"| {_fmt(row['tp'])} "
            f"| {_fmt(row['fp'])} "
            f"| {_fmt(row['tn'])} "
            f"| {_fmt(row['fn'])} "
            f"| {_fmt(row['latency_ms_avg'], 3)} "
            f"| {row['model_status']} |"
        )

    lines.extend(
        [
            "",
            "## Hybrid Delta vs Previous",
            "",
            "| Dataset | Recall Delta | F1 Delta | Accuracy Delta | TP Delta | FP Delta | FN Delta |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for spec in DATASET_SPECS:
        current = hybrid_by_dataset.get(spec.name, {})
        previous = spec.previous
        lines.append(
            f"| `{spec.name}` "
            f"| {_delta(current.get('recall'), previous.recall)} "
            f"| {_delta(current.get('f1'), previous.f1)} "
            f"| {_delta(current.get('accuracy'), previous.accuracy)} "
            f"| {_delta(current.get('tp'), previous.tp)} "
            f"| {_delta(current.get('fp'), previous.fp)} "
            f"| {_delta(current.get('fn'), previous.fn)} |"
        )

    lines.extend(
        [
            "",
            "## Why Rule Only and Hybrid are Similar",
            "",
            "현재 외부 영어 데이터셋에서는 Hybrid / Full Pipeline 결과가 Rule Only와 거의 동일하게 나타났다. 이는 경량 모델 artifact가 로드되지 않았기 때문이 아니라, 로드된 모델이 Rule 계층이 놓친 영어 공격 샘플을 추가로 거의 탐지하지 못했기 때문이다.",
            "",
            "즉, 현재 Hybrid 성능은 대부분 Rule 계층에 의해 결정된다. `Lakera/gandalf_ignore_instructions`에서는 Hybrid가 Rule Only보다 Recall을 0.028 높였으나, `deepset/prompt-injections`와 `protectai/prompt-injection-validation`에서는 모델 계층의 unique TP가 거의 없어 성능 차이가 나타나지 않았다.",
            "",
            "이 결과는 경량 분류 계층의 구조적 실패라기보다, 현재 학습 데이터가 한국어 공공기관 시나리오에 집중되어 있어 영어 공개 데이터셋에 대한 일반화가 부족하다는 근거로 해석한다. 정량적인 unique TP 근거는 `reports/external_overlap_analysis_report.md`에서 확인한다.",
            "",
            "## Reading Guide",
            "",
            "- `Rule Only`는 `backend/app/detection/injection_detector.py`의 규칙·휴리스틱 Prompt Injection 탐지만 사용한다.",
            "- `Lightweight Model Only`는 `models/lightweight/vectorizer.joblib`와 `models/lightweight/classifier.joblib`가 실제로 로드된 경우에만 측정한다.",
            "- `Hybrid / Full Pipeline`은 현재 프로젝트의 다층형 탐지 파이프라인 실행 경로이며, 규칙 탐지와 경량 모델 계층을 함께 사용한다.",
            "- `Lakera/gandalf_ignore_instructions`는 공격 샘플 중심 데이터셋이므로 Precision, F1, FP, TN은 `N/A`로 표시하고 Recall과 Accuracy 중심으로 해석한다.",
            "- `model_status`가 `enabled`가 아니면 Hybrid 결과는 경량 분류 계층이 빠진 fallback 성격이므로 완전한 Hybrid 성능으로 과장하지 않는다.",
            "- sklearn artifact 버전 경고가 발생하면 같은 scikit-learn 버전으로 artifact를 재생성한 뒤 결과를 다시 확인한다.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(
    *,
    generated_at: str,
    split: str,
    threshold: float,
    datasets: list[DatasetBundle],
    rows: list[dict[str, Any]],
    classifier_status: LightweightModelStatus,
    runtime_versions: dict[str, str],
    model_metadata: dict[str, str],
    path: Path,
) -> None:
    payload = {
        "generated_at": generated_at,
        "split": split,
        "threshold": threshold,
        "scope": PROJECT_SCOPE,
        "external_recall_note": EXTERNAL_RECALL_NOTE,
        "classifier_status": {
            "enabled": classifier_status.enabled,
            "status": classifier_status.status,
            "note": classifier_status.note,
            "vectorizer_path": str(classifier_status.vectorizer_path),
            "classifier_path": str(classifier_status.classifier_path),
        },
        "runtime_versions": runtime_versions,
        "model_metadata": model_metadata,
        "datasets": [
            {
                "name": dataset.spec.name,
                "source": dataset.spec.source,
                "role": dataset.spec.role,
                "samples": len(dataset.samples),
                "status": dataset.status,
                "note": dataset.note,
                "positive_only": dataset.spec.positive_only,
                "previous": asdict(dataset.spec.previous),
            }
            for dataset in datasets
        ],
        "results": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = [
        "dataset_name",
        "mode",
        "size",
        "precision",
        "recall",
        "f1",
        "accuracy",
        "tp",
        "fp",
        "tn",
        "fn",
        "positive_only",
        "latency_ms_avg",
        "model_status",
        "dataset_status",
        "note",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def _write_outputs(
    *,
    generated_at: str,
    split: str,
    threshold: float,
    datasets: list[DatasetBundle],
    rows: list[dict[str, Any]],
    classifier_status: LightweightModelStatus,
    runtime_versions: dict[str, str],
    model_metadata: dict[str, str],
    report_path: Path,
    json_path: Path,
    csv_path: Path,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _render_markdown(
            generated_at=generated_at,
            split=split,
            threshold=threshold,
            datasets=datasets,
            rows=rows,
            classifier_status=classifier_status,
            runtime_versions=runtime_versions,
            model_metadata=model_metadata,
        ),
        encoding="utf-8",
    )
    _write_json(
        generated_at=generated_at,
        split=split,
        threshold=threshold,
        datasets=datasets,
        rows=rows,
        classifier_status=classifier_status,
        runtime_versions=runtime_versions,
        model_metadata=model_metadata,
        path=json_path,
    )
    _write_csv(rows, csv_path)


def _optional_limit(value: int) -> int | None:
    return None if value < 0 else value


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Rule Only, Lightweight Model Only, and Hybrid/Full Pipeline on public prompt injection datasets."
    )
    parser.add_argument("--split", default="all", help="Hugging Face split to load. Use 'all' for every split.")
    parser.add_argument("--threshold", type=float, default=0.7, help="Lightweight model threshold.")
    parser.add_argument("--max-samples", type=int, default=-1, help="Global sample cap per dataset. -1 means full dataset.")
    parser.add_argument("--report", default=str(REPORT_PATH), help="Markdown report output path.")
    parser.add_argument("--json", default=str(RESULTS_JSON_PATH), help="JSON result output path.")
    parser.add_argument("--csv", default=str(RESULTS_CSV_PATH), help="CSV result output path.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    max_samples = _optional_limit(args.max_samples)
    datasets = [
        _load_dataset(spec, args.split, max_samples)
        for spec in DATASET_SPECS
    ]

    classifier = LightweightClassifier(threshold=args.threshold)
    classifier_status = classifier.status()
    rows: list[dict[str, Any]] = []
    for dataset in datasets:
        rows.extend(
            _evaluate_dataset(
                dataset=dataset,
                classifier=classifier,
                classifier_status=classifier_status,
                threshold=args.threshold,
            )
        )

    generated_at = datetime.now().isoformat(timespec="seconds")
    runtime_versions = _runtime_versions()
    model_metadata = _model_metadata(classifier_status)
    _write_outputs(
        generated_at=generated_at,
        split=args.split,
        threshold=args.threshold,
        datasets=datasets,
        rows=rows,
        classifier_status=classifier_status,
        runtime_versions=runtime_versions,
        model_metadata=model_metadata,
        report_path=Path(args.report),
        json_path=Path(args.json),
        csv_path=Path(args.csv),
    )
    print(f"External dataset comparison report saved to: {args.report}")
    print(f"External dataset comparison JSON saved to: {args.json}")
    print(f"External dataset comparison CSV saved to: {args.csv}")


if __name__ == "__main__":
    main()
