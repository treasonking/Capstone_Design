from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.external_dataset_compare import (
    DATASET_SPECS,
    DEFAULT_EVAL_PATH,
    _apply_model_version_override,
    _classifier_from_model_dir,
    _fmt,
    _load_dataset,
    _load_eval_path,
    _model_metadata,
    _optional_limit,
    _runtime_versions,
    _safe_div,
)


CONFIDENCE_REPORT_PATH = Path("reports/external_model_confidence_report.md")
CONFIDENCE_JSON_PATH = Path("reports/external_model_confidence_results.json")
THRESHOLDS = (0.3, 0.5, 0.7)


def _probability_view(classifier: LightweightClassifier, text: str) -> dict[str, Any]:
    prediction = classifier.classify(text)
    predicted_label = prediction.label.strip().upper()
    top_confidence = float(prediction.confidence)
    injection_confidence = 0.0

    vectorizer = getattr(classifier, "_vectorizer", None)
    estimator = getattr(classifier, "_classifier", None)
    if vectorizer is not None and estimator is not None and hasattr(estimator, "predict_proba"):
        features = vectorizer.transform([text])
        probabilities = estimator.predict_proba(features)[0]
        classes = [str(item).strip().upper() for item in getattr(estimator, "classes_", [])]
        injection_indices = [
            idx
            for idx, label in enumerate(classes)
            if "INJ" in label or "INJECTION" in label or "PROMPT" in label or "JAILBREAK" in label
        ]
        if injection_indices:
            injection_confidence = max(float(probabilities[idx]) for idx in injection_indices)

    return {
        "predicted_label": predicted_label,
        "top_confidence": top_confidence,
        "injection_confidence": injection_confidence,
        "detected": prediction.detected,
        "source": prediction.source,
    }


def _rate(values: list[float], threshold: float) -> float:
    return _safe_div(sum(1 for value in values if value >= threshold), len(values))


def _summarize_group(
    *,
    dataset_name: str,
    label: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    top_values = [float(row["top_confidence"]) for row in rows]
    injection_values = [float(row["injection_confidence"]) for row in rows]
    return {
        "dataset_name": dataset_name,
        "label": label,
        "count": len(rows),
        "avg_confidence": mean(top_values) if top_values else None,
        "confidence_gte_0_3": _rate(top_values, 0.3),
        "confidence_gte_0_5": _rate(top_values, 0.5),
        "confidence_gte_0_7": _rate(top_values, 0.7),
        "avg_injection_confidence": mean(injection_values) if injection_values else None,
        "injection_confidence_gte_0_3": _rate(injection_values, 0.3),
        "injection_confidence_gte_0_5": _rate(injection_values, 0.5),
        "injection_confidence_gte_0_7": _rate(injection_values, 0.7),
    }


def _analyze(
    *,
    split: str,
    eval_path: Path | None,
    model_dir: Path | None,
    model_version_override: str | None,
    max_samples: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    classifier = _classifier_from_model_dir(model_dir, 0.7)
    classifier_status = classifier.status()
    model_metadata = _apply_model_version_override(
        _model_metadata(classifier_status),
        model_version_override,
    )
    summaries: list[dict[str, Any]] = []
    label_distribution: list[dict[str, Any]] = []
    datasets = (
        _load_eval_path(eval_path, max_samples)
        if eval_path is not None
        else [_load_dataset(spec, split, max_samples) for spec in DATASET_SPECS]
    )

    for dataset in datasets:
        spec = dataset.spec
        if dataset.status != "loaded" or not dataset.samples:
            summaries.append(
                {
                    "dataset_name": spec.name,
                    "label": "unavailable",
                    "count": 0,
                    "avg_confidence": None,
                    "confidence_gte_0_3": None,
                    "confidence_gte_0_5": None,
                    "confidence_gte_0_7": None,
                    "avg_injection_confidence": None,
                    "injection_confidence_gte_0_3": None,
                    "injection_confidence_gte_0_5": None,
                    "injection_confidence_gte_0_7": None,
                    "dataset_status": dataset.status,
                    "note": dataset.note,
                }
            )
            continue

        prediction_rows: list[dict[str, Any]] = []
        distribution = Counter()
        for sample in dataset.samples:
            view = _probability_view(classifier, sample.text)
            expected_label = "injection" if sample.expected_injection else "benign"
            distribution[view["predicted_label"]] += 1
            prediction_rows.append(
                {
                    "expected_label": expected_label,
                    **view,
                }
            )

        for expected_label in ("injection", "benign"):
            group = [
                row
                for row in prediction_rows
                if row["expected_label"] == expected_label
            ]
            if not group:
                continue
            summary = _summarize_group(
                dataset_name=spec.name,
                label=expected_label,
                rows=group,
            )
            summary["dataset_status"] = dataset.status
            summary["note"] = dataset.note
            summaries.append(summary)

        for predicted_label, count in sorted(distribution.items()):
            label_distribution.append(
                {
                    "dataset_name": spec.name,
                    "predicted_label": predicted_label,
                    "count": count,
                }
            )

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
    return summaries, label_distribution, metadata


def _render_report(
    *,
    generated_at: str,
    split: str,
    summaries: list[dict[str, Any]],
    label_distribution: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> str:
    lines = [
        "# External Model Confidence Analysis",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Hugging Face split: `{split}`",
        f"- Model status: `{metadata['classifier_status']['status']}`",
        f"- Model version: `{metadata['model_metadata']['model_version']}`",
        "",
        "## Confidence by Expected Label",
        "",
        "| Dataset | Label | Count | Avg Confidence | >=0.3 | >=0.5 | >=0.7 | Avg Injection Confidence | Inj >=0.3 | Inj >=0.5 | Inj >=0.7 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| `{row['dataset_name']}` "
            f"| {row['label']} "
            f"| {_fmt(row['count'])} "
            f"| {_fmt(row['avg_confidence'])} "
            f"| {_fmt(row['confidence_gte_0_3'])} "
            f"| {_fmt(row['confidence_gte_0_5'])} "
            f"| {_fmt(row['confidence_gte_0_7'])} "
            f"| {_fmt(row['avg_injection_confidence'])} "
            f"| {_fmt(row['injection_confidence_gte_0_3'])} "
            f"| {_fmt(row['injection_confidence_gte_0_5'])} "
            f"| {_fmt(row['injection_confidence_gte_0_7'])} |"
        )

    lines.extend(
        [
            "",
            "## Predicted Label Distribution",
            "",
            "| Dataset | Predicted Label | Count |",
            "|---|---|---:|",
        ]
    )
    for row in label_distribution:
        lines.append(
            f"| `{row['dataset_name']}` | {row['predicted_label']} | {row['count']} |"
        )

    lines.extend(
        [
            "",
            "## Observed Conclusion",
            "",
            "- confidence 분포는 threshold 문제가 큰지, label 학습/일반화 문제가 큰지 구분하기 위한 보조 근거다.",
            "- external-tuned 모델에서는 injection label confidence가 상승했지만, 운영 threshold를 낮출 때는 benign 샘플의 injection confidence와 FP를 함께 확인해야 한다.",
            "- label mapping이 정상이라면 predicted label 분포에서 INJECTION 계열 label이 실제 공격 샘플에 충분히 나타나야 한다.",
            "",
            "## Interpretation",
            "",
            "- `Avg Confidence`는 모델이 선택한 top label의 confidence다.",
            "- `Avg Injection Confidence`는 classifier probability 중 injection 계열 label의 confidence다.",
            "- injection 샘플의 top confidence는 높지만 predicted label이 대부분 SAFE/PII이면 threshold 문제가 아니라 label 학습/일반화 문제에 가깝다.",
            "- injection confidence가 전반적으로 낮으면 threshold를 낮춰도 Recall 개선 폭이 제한될 수 있다.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(
    *,
    generated_at: str,
    split: str,
    summaries: list[dict[str, Any]],
    label_distribution: list[dict[str, Any]],
    metadata: dict[str, Any],
    path: Path,
) -> None:
    payload = {
        "generated_at": generated_at,
        "split": split,
        **metadata,
        "confidence_summary": summaries,
        "predicted_label_distribution": label_distribution,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze lightweight model confidence distribution on external datasets."
    )
    parser.add_argument("--split", default="all", help="Hugging Face split to load.")
    parser.add_argument(
        "--eval-path",
        default=str(DEFAULT_EVAL_PATH),
        help="Held-out external eval JSONL path. Use an empty string to load Hugging Face splits directly.",
    )
    parser.add_argument(
        "--model-dir",
        default="",
        help="Directory containing vectorizer.joblib and classifier.joblib. Defaults to models/lightweight.",
    )
    parser.add_argument("--model-version", default="", help="Model version label to record in report metadata.")
    parser.add_argument("--max-samples", type=int, default=-1, help="Sample cap per dataset. -1 means full dataset.")
    parser.add_argument("--report", default=str(CONFIDENCE_REPORT_PATH), help="Markdown report output path.")
    parser.add_argument("--json", default=str(CONFIDENCE_JSON_PATH), help="JSON output path.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    eval_path = Path(args.eval_path) if args.eval_path else None
    summaries, label_distribution, metadata = _analyze(
        split=args.split,
        eval_path=eval_path,
        model_dir=Path(args.model_dir) if args.model_dir else None,
        model_version_override=args.model_version or None,
        max_samples=_optional_limit(args.max_samples),
    )
    generated_at = datetime.now().isoformat(timespec="seconds")
    report = _render_report(
        generated_at=generated_at,
        split=str(eval_path) if eval_path is not None else args.split,
        summaries=summaries,
        label_distribution=label_distribution,
        metadata=metadata,
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    _write_json(
        generated_at=generated_at,
        split=str(eval_path) if eval_path is not None else args.split,
        summaries=summaries,
        label_distribution=label_distribution,
        metadata=metadata,
        path=Path(args.json),
    )
    print(f"External model confidence report saved to: {args.report}")
    print(f"External model confidence JSON saved to: {args.json}")


if __name__ == "__main__":
    main()
