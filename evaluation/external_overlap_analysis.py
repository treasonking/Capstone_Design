from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import DetectionSettings
from backend.app.detection.hybrid_detector import detect_hybrid
from backend.app.detection.injection_detector import detect_injection
from backend.app.detection.lightweight_classifier import LightweightClassifier
from backend.app.detection.models import DetectorType
from evaluation.external_dataset_compare import (
    DATASET_SPECS,
    _apply_model_version_override,
    _classifier_from_model_dir,
    _fmt,
    _is_model_injection_prediction,
    _load_dataset,
    _load_eval_path,
    _model_metadata,
    _optional_limit,
    _runtime_versions,
)
from evaluation.prompt_injection_fusion import (
    fuse_prompt_injection_decision,
    prompt_injection_model_score,
)


OVERLAP_REPORT_PATH = Path("reports/external_overlap_analysis_report.md")
OVERLAP_JSON_PATH = Path("reports/external_overlap_analysis_results.json")
OVERLAP_CSV_PATH = Path("reports/external_overlap_analysis_results.csv")


def _hybrid_pipeline_prediction(
    text: str,
    classifier: LightweightClassifier,
    threshold: float,
) -> tuple[bool, bool]:
    settings = DetectionSettings(
        enable_model_detector=True,
        detection_mode="hybrid",
        model_detector_threshold=threshold,
        model_detector_fail_mode="warn",
    )
    result = detect_hybrid(text, classifier=classifier, settings=settings)
    pipeline_predicted = any(
        detection.detector_type == DetectorType.INJECTION
        for detection in result.detections
    )
    model_injection_detection = any(
        detection.detector_type == DetectorType.INJECTION
        and detection.detector_name == "llm"
        for detection in result.detections
    )
    model_hit_cancelled_by_safe_guard = (
        result.model_prediction is not None
        and _is_model_injection_prediction(result.model_prediction)
        and not model_injection_detection
        and "SAFE_SECURITY_EXPLANATION" in result.reason_codes
    )
    return pipeline_predicted, model_hit_cancelled_by_safe_guard


def _analyze_dataset(
    *,
    dataset_name: str,
    model_version: str,
    samples: list[Any],
    classifier: LightweightClassifier,
    threshold: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sample_rows: list[dict[str, Any]] = []

    for sample in samples:
        rule_hits = detect_injection(sample.text)
        rule_predicted = bool(rule_hits)
        model_prediction = classifier.classify(sample.text)
        model_predicted = _is_model_injection_prediction(model_prediction)
        model_score = prompt_injection_model_score(
            classifier,
            sample.text,
            model_prediction,
            model_predicted,
        )
        fusion = fuse_prompt_injection_decision(
            model_predicted=model_predicted,
            model_score=model_score,
            rule_hits=rule_hits,
            text=sample.text,
        )
        hybrid_pipeline_predicted, model_hit_cancelled_by_safe_guard = _hybrid_pipeline_prediction(
            sample.text,
            classifier,
            threshold,
        )
        hybrid_predicted = fusion.predicted
        expected = bool(sample.expected_injection)
        sample_rows.append(
            {
                "dataset_name": dataset_name,
                "model_version": model_version,
                "id": sample.id,
                "expected_injection": expected,
                "rule_predicted": rule_predicted,
                "model_predicted": model_predicted,
                "hybrid_predicted": hybrid_predicted,
                "hybrid_pipeline_predicted": hybrid_pipeline_predicted,
                "model_hit_cancelled_by_safe_guard": model_hit_cancelled_by_safe_guard,
                "model_label": model_prediction.label,
                "model_confidence": model_prediction.confidence,
                "model_score": model_score,
                "hybrid_final_action": fusion.final_action,
            }
        )

    rule_tp = sum(1 for row in sample_rows if row["expected_injection"] and row["rule_predicted"])
    model_tp = sum(1 for row in sample_rows if row["expected_injection"] and row["model_predicted"])
    both_tp = sum(
        1
        for row in sample_rows
        if row["expected_injection"] and row["rule_predicted"] and row["model_predicted"]
    )
    rule_only_tp = sum(
        1
        for row in sample_rows
        if row["expected_injection"] and row["rule_predicted"] and not row["model_predicted"]
    )
    model_only_unique_tp = sum(
        1
        for row in sample_rows
        if row["expected_injection"] and row["model_predicted"] and not row["rule_predicted"]
    )
    hybrid_tp = sum(
        1
        for row in sample_rows
        if row["expected_injection"] and row["hybrid_predicted"]
    )
    hybrid_extra_tp = sum(
        1
        for row in sample_rows
        if row["expected_injection"] and row["hybrid_predicted"] and not row["rule_predicted"]
    )
    hybrid_pipeline_tp = sum(
        1
        for row in sample_rows
        if row["expected_injection"] and row["hybrid_pipeline_predicted"]
    )
    model_hit_cancelled_by_safe_guard_count = sum(
        1 for row in sample_rows if row["model_hit_cancelled_by_safe_guard"]
    )
    model_hit_cancelled_by_safe_guard_tp = sum(
        1
        for row in sample_rows
        if row["expected_injection"] and row["model_hit_cancelled_by_safe_guard"]
    )

    summary = {
        "dataset_name": dataset_name,
        "model_version": model_version,
        "size": len(sample_rows),
        "attack_samples": sum(1 for row in sample_rows if row["expected_injection"]),
        "rule_tp": rule_tp,
        "model_tp": model_tp,
        "both_tp": both_tp,
        "rule_only_tp": rule_only_tp,
        "model_only_unique_tp": model_only_unique_tp,
        "hybrid_tp": hybrid_tp,
        "hybrid_extra_tp": hybrid_extra_tp,
        "hybrid_pipeline_tp": hybrid_pipeline_tp,
        "model_hit_cancelled_by_safe_guard_count": model_hit_cancelled_by_safe_guard_count,
        "model_hit_cancelled_by_safe_guard_tp": model_hit_cancelled_by_safe_guard_tp,
        "hybrid_tp_equals_rule_plus_model_unique": hybrid_tp == rule_tp + model_only_unique_tp,
        "hybrid_tp_equals_rule_plus_hybrid_extra": hybrid_tp == rule_tp + hybrid_extra_tp,
    }
    return summary, sample_rows


def _run_analysis(
    *,
    threshold: float,
    split: str,
    eval_path: Path | None,
    model_dir: Path | None,
    model_version_override: str | None,
    max_samples: int | None,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, Any]]:
    classifier = _classifier_from_model_dir(model_dir, threshold)
    classifier_status = classifier.status()
    model_metadata = _apply_model_version_override(
        _model_metadata(classifier_status),
        model_version_override,
    )
    model_version = model_metadata["model_version"]
    summaries: list[dict[str, Any]] = []
    sample_predictions: dict[str, list[dict[str, Any]]] = {}
    datasets = (
        _load_eval_path(eval_path, max_samples)
        if eval_path is not None
        else [_load_dataset(spec, split, max_samples) for spec in DATASET_SPECS]
    )

    for dataset in datasets:
        if dataset.status != "loaded" or not dataset.samples:
            summaries.append(
                {
                    "dataset_name": dataset.spec.name,
                    "model_version": model_version,
                    "size": len(dataset.samples),
                    "attack_samples": None,
                    "rule_tp": None,
                    "model_tp": None,
                    "both_tp": None,
                    "rule_only_tp": None,
                    "model_only_unique_tp": None,
                    "hybrid_tp": None,
                    "hybrid_extra_tp": None,
                    "hybrid_pipeline_tp": None,
                    "model_hit_cancelled_by_safe_guard_count": None,
                    "model_hit_cancelled_by_safe_guard_tp": None,
                    "hybrid_tp_equals_rule_plus_model_unique": None,
                    "hybrid_tp_equals_rule_plus_hybrid_extra": None,
                    "dataset_status": dataset.status,
                    "note": dataset.note,
                }
            )
            sample_predictions[dataset.spec.name] = []
            continue

        summary, samples = _analyze_dataset(
            dataset_name=dataset.spec.name,
            model_version=model_version,
            samples=dataset.samples,
            classifier=classifier,
            threshold=threshold,
        )
        summary["dataset_status"] = dataset.status
        summary["note"] = dataset.note
        summaries.append(summary)
        sample_predictions[dataset.spec.name] = samples

    metadata = {
        "classifier_status": {
            "enabled": classifier_status.enabled,
            "status": classifier_status.status,
            "note": classifier_status.note,
            "vectorizer_path": str(classifier_status.vectorizer_path),
            "classifier_path": str(classifier_status.classifier_path),
        },
        "model_metadata": model_metadata,
        "runtime_versions": _runtime_versions(),
    }
    return summaries, sample_predictions, metadata


def _render_report(
    *,
    generated_at: str,
    threshold: float,
    split: str,
    summaries: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> str:
    lines = [
        "# External Rule/Model Overlap Analysis",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Hugging Face split: `{split}`",
        f"- Lightweight threshold: `{threshold:.2f}`",
        f"- Model status: `{metadata['classifier_status']['status']}`",
        f"- Model version: `{metadata['model_metadata']['model_version']}`",
        "",
        "## Summary",
        "",
        "| Dataset | Model Version | Rule TP | Model TP | Both TP | Rule Only TP | Model Only Unique TP | Hybrid TP | Hybrid Extra TP | Pipeline TP | Safe Guard Cancelled Model Hits | Cancelled TP |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| `{row['dataset_name']}` "
            f"| {row.get('model_version', metadata['model_metadata']['model_version'])} "
            f"| {_fmt(row['rule_tp'])} "
            f"| {_fmt(row['model_tp'])} "
            f"| {_fmt(row['both_tp'])} "
            f"| {_fmt(row['rule_only_tp'])} "
            f"| {_fmt(row['model_only_unique_tp'])} "
            f"| {_fmt(row['hybrid_tp'])} "
            f"| {_fmt(row['hybrid_extra_tp'])} "
            f"| {_fmt(row['hybrid_pipeline_tp'])} "
            f"| {_fmt(row['model_hit_cancelled_by_safe_guard_count'])} "
            f"| {_fmt(row['model_hit_cancelled_by_safe_guard_tp'])} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Hybrid / Full Pipeline 성능이 Rule Only와 유사하게 나타나는 경우, 주된 이유는 Lightweight Model이 Rule 계층이 놓친 공격 샘플을 거의 추가로 탐지하지 못하기 때문이다.",
            "",
            "반대로 external-tuned 모델처럼 `Model Only Unique TP`가 증가하면 calibrated Hybrid TP도 Rule TP보다 커진다. 따라서 이 표는 Hybrid 개선 여부를 모델 계층의 독립 기여도로 설명하는 핵심 근거다.",
            "",
            "`Hybrid TP`와 `Hybrid Extra TP`는 PII rule을 제외한 calibrated prompt-injection fusion 기준이다. `Pipeline TP`는 운영용 `detect_hybrid()` 실행 결과이며, benchmark fusion과의 차이는 별도로 해석한다.",
            "",
            "샘플 단위의 `expected_injection`, `rule_predicted`, `model_predicted`, `hybrid_predicted` 값은 JSON 결과 파일의 `sample_predictions`에 저장한다.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(
    *,
    generated_at: str,
    threshold: float,
    split: str,
    summaries: list[dict[str, Any]],
    sample_predictions: dict[str, list[dict[str, Any]]],
    metadata: dict[str, Any],
    path: Path,
) -> None:
    payload = {
        "generated_at": generated_at,
        "threshold": threshold,
        "split": split,
        **metadata,
        "results": summaries,
        "sample_predictions": sample_predictions,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = [
        "dataset_name",
        "model_version",
        "size",
        "attack_samples",
        "rule_tp",
        "model_tp",
        "both_tp",
        "rule_only_tp",
        "model_only_unique_tp",
        "hybrid_tp",
        "hybrid_extra_tp",
        "hybrid_pipeline_tp",
        "model_hit_cancelled_by_safe_guard_count",
        "model_hit_cancelled_by_safe_guard_tp",
        "hybrid_tp_equals_rule_plus_model_unique",
        "hybrid_tp_equals_rule_plus_hybrid_extra",
        "dataset_status",
        "note",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze overlap between Rule Only, Lightweight Model Only, and Hybrid predictions."
    )
    parser.add_argument("--threshold", type=float, default=0.7, help="Lightweight model threshold.")
    parser.add_argument("--split", default="all", help="Hugging Face split to load.")
    parser.add_argument(
        "--eval-path",
        default="",
        help="Held-out external eval JSONL path. When set, this replaces direct Hugging Face split loading.",
    )
    parser.add_argument(
        "--model-dir",
        default="",
        help="Directory containing vectorizer.joblib and classifier.joblib. Defaults to models/lightweight.",
    )
    parser.add_argument(
        "--model-version",
        default="",
        help="Model version label to record in result rows.",
    )
    parser.add_argument("--max-samples", type=int, default=-1, help="Sample cap per dataset. -1 means full dataset.")
    parser.add_argument("--report", default=str(OVERLAP_REPORT_PATH), help="Markdown report output path.")
    parser.add_argument("--json", default=str(OVERLAP_JSON_PATH), help="JSON output path.")
    parser.add_argument("--csv", default=str(OVERLAP_CSV_PATH), help="CSV output path.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    summaries, sample_predictions, metadata = _run_analysis(
        threshold=args.threshold,
        split=args.split,
        eval_path=Path(args.eval_path) if args.eval_path else None,
        model_dir=Path(args.model_dir) if args.model_dir else None,
        model_version_override=args.model_version or None,
        max_samples=_optional_limit(args.max_samples),
    )
    generated_at = datetime.now().isoformat(timespec="seconds")
    report = _render_report(
        generated_at=generated_at,
        threshold=args.threshold,
        split=args.eval_path or args.split,
        summaries=summaries,
        metadata=metadata,
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    _write_json(
        generated_at=generated_at,
        threshold=args.threshold,
        split=args.eval_path or args.split,
        summaries=summaries,
        sample_predictions=sample_predictions,
        metadata=metadata,
        path=Path(args.json),
    )
    _write_csv(summaries, Path(args.csv))
    print(f"External overlap analysis report saved to: {args.report}")
    print(f"External overlap analysis JSON saved to: {args.json}")
    print(f"External overlap analysis CSV saved to: {args.csv}")


if __name__ == "__main__":
    main()
