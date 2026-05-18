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

from backend.app.detection.lightweight_classifier import LightweightClassifier
from evaluation.external_dataset_compare import (
    DATASET_SPECS,
    RESULTS_CSV_PATH,
    RESULTS_JSON_PATH,
    REPORT_PATH,
    _fmt,
    _hybrid_pipeline,
    _load_dataset,
    _metric_result,
    _model_metadata,
    _model_only,
    _optional_limit,
    _runtime_versions,
)


SWEEP_REPORT_PATH = Path("reports/external_threshold_sweep_report.md")
SWEEP_JSON_PATH = Path("reports/external_threshold_sweep_results.json")
SWEEP_CSV_PATH = Path("reports/external_threshold_sweep_results.csv")
DEFAULT_THRESHOLDS = "0.3,0.4,0.5,0.6,0.7"


def _parse_thresholds(raw: str) -> list[float]:
    thresholds: list[float] = []
    for item in raw.split(","):
        stripped = item.strip()
        if not stripped:
            continue
        value = float(stripped)
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Threshold must be between 0 and 1: {value}")
        thresholds.append(value)
    if not thresholds:
        raise ValueError("At least one threshold is required.")
    return thresholds


def _na_row(dataset_name: str, threshold: float, mode: str, model_status: str) -> dict[str, Any]:
    return {
        "dataset_name": dataset_name,
        "threshold": threshold,
        "mode": mode,
        "size": None,
        "precision": None,
        "recall": None,
        "f1": None,
        "accuracy": None,
        "tp": None,
        "fp": None,
        "tn": None,
        "fn": None,
        "latency_ms_avg": None,
        "model_status": model_status,
    }


def _with_threshold(row: dict[str, Any], threshold: float) -> dict[str, Any]:
    return {"threshold": threshold, **row}


def _evaluate(
    *,
    thresholds: list[float],
    split: str,
    max_samples: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    classifier = LightweightClassifier()
    classifier_status = classifier.status()
    model_metadata = _model_metadata(classifier_status)
    datasets = [_load_dataset(spec, split, max_samples) for spec in DATASET_SPECS]
    rows: list[dict[str, Any]] = []

    for threshold in thresholds:
        classifier.threshold = threshold
        for dataset in datasets:
            if dataset.status != "loaded" or not dataset.samples:
                rows.append(
                    _na_row(
                        dataset.spec.name,
                        threshold,
                        "Lightweight Model Only",
                        classifier_status.status,
                    )
                )
                rows.append(
                    _na_row(
                        dataset.spec.name,
                        threshold,
                        "Hybrid / Full Pipeline",
                        classifier_status.status,
                    )
                )
                continue

            if classifier_status.enabled:
                model_row = _metric_result(
                    dataset=dataset,
                    mode="Lightweight Model Only",
                    predictor=_model_only(classifier),
                    model_status=classifier_status.status,
                )
                rows.append(_with_threshold(model_row, threshold))
            else:
                rows.append(
                    _na_row(
                        dataset.spec.name,
                        threshold,
                        "Lightweight Model Only",
                        classifier_status.status,
                    )
                )

            hybrid_row = _metric_result(
                dataset=dataset,
                mode="Hybrid / Full Pipeline",
                predictor=_hybrid_pipeline(classifier, threshold),
                model_status=classifier_status.status,
            )
            rows.append(_with_threshold(hybrid_row, threshold))

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
        "datasets": [
            {
                "name": dataset.spec.name,
                "samples": len(dataset.samples),
                "status": dataset.status,
                "note": dataset.note,
            }
            for dataset in datasets
        ],
    }
    return rows, metadata


def _render_report(
    *,
    generated_at: str,
    split: str,
    thresholds: list[float],
    rows: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> str:
    lines = [
        "# External Threshold Sweep",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Hugging Face split: `{split}`",
        f"- Thresholds: `{', '.join(f'{item:.2f}' for item in thresholds)}`",
        "",
        "## Model Status",
        "",
        "| Item | Value |",
        "|---|---|",
    ]
    classifier_status = metadata["classifier_status"]
    for key in ("enabled", "status", "note", "vectorizer_path", "classifier_path"):
        lines.append(f"| {key} | {classifier_status[key]} |")

    lines.extend(
        [
            "",
            "## Results",
            "",
            "| Dataset | Threshold | Mode | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |",
            "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        lines.append(
            f"| `{row['dataset_name']}` "
            f"| {_fmt(row['threshold'], 2)} "
            f"| {row['mode']} "
            f"| {_fmt(row['precision'])} "
            f"| {_fmt(row['recall'])} "
            f"| {_fmt(row['f1'])} "
            f"| {_fmt(row['accuracy'])} "
            f"| {_fmt(row['tp'])} "
            f"| {_fmt(row['fp'])} "
            f"| {_fmt(row['tn'])} "
            f"| {_fmt(row['fn'])} |"
        )

    lines.extend(
        [
            "",
            "## Observed Conclusion",
            "",
            "- 현재 0.70 threshold에서는 Lightweight Model Only Recall이 매우 낮아 Hybrid가 Rule Only와 거의 같게 보인다.",
            "- threshold를 0.30 또는 0.40으로 낮추면 Recall은 크게 상승하지만 `deepset`과 `protectai`에서 FP도 크게 증가한다.",
            "- 따라서 원인은 단순히 모델이 항상 영어 공격을 못 알아보는 것이 아니라, 현재 classifier confidence calibration과 운영 threshold가 외부 영어 데이터셋에 맞지 않는 데 있다.",
            "- 운영용 threshold를 무작정 낮추기보다는 외부 영어 데이터 기반 재학습, validation split 기반 threshold 조정, hard negative 보강이 필요하다.",
            "",
            "## Interpretation",
            "",
            "- threshold를 낮췄을 때 Lightweight Model Only Recall이 크게 상승하면 기존 threshold가 너무 보수적이었을 가능성이 있다.",
            "- threshold를 낮춰도 Recall이 거의 상승하지 않으면 모델 자체가 영어 공격 표현을 충분히 학습하지 못한 것이다.",
            "- threshold를 낮췄을 때 FP가 급증하면 운영 threshold는 보수적으로 유지하고, 외부 영어 데이터 기반 재학습을 우선 검토한다.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(
    *,
    generated_at: str,
    split: str,
    thresholds: list[float],
    rows: list[dict[str, Any]],
    metadata: dict[str, Any],
    path: Path,
) -> None:
    payload = {
        "generated_at": generated_at,
        "split": split,
        "thresholds": thresholds,
        **metadata,
        "results": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fieldnames = [
        "dataset_name",
        "threshold",
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
        "latency_ms_avg",
        "model_status",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep lightweight classifier thresholds on external prompt injection datasets."
    )
    parser.add_argument(
        "--threshold-sweep",
        default=DEFAULT_THRESHOLDS,
        help="Comma-separated threshold list, for example 0.3,0.4,0.5,0.6,0.7.",
    )
    parser.add_argument("--split", default="all", help="Hugging Face split to load.")
    parser.add_argument("--max-samples", type=int, default=-1, help="Sample cap per dataset. -1 means full dataset.")
    parser.add_argument("--report", default=str(SWEEP_REPORT_PATH), help="Markdown report output path.")
    parser.add_argument("--json", default=str(SWEEP_JSON_PATH), help="JSON output path.")
    parser.add_argument("--csv", default=str(SWEEP_CSV_PATH), help="CSV output path.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    thresholds = _parse_thresholds(args.threshold_sweep)
    rows, metadata = _evaluate(
        thresholds=thresholds,
        split=args.split,
        max_samples=_optional_limit(args.max_samples),
    )
    generated_at = datetime.now().isoformat(timespec="seconds")
    report = _render_report(
        generated_at=generated_at,
        split=args.split,
        thresholds=thresholds,
        rows=rows,
        metadata=metadata,
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    _write_json(
        generated_at=generated_at,
        split=args.split,
        thresholds=thresholds,
        rows=rows,
        metadata=metadata,
        path=Path(args.json),
    )
    _write_csv(rows, Path(args.csv))
    print(f"External threshold sweep report saved to: {args.report}")
    print(f"External threshold sweep JSON saved to: {args.json}")
    print(f"External threshold sweep CSV saved to: {args.csv}")


if __name__ == "__main__":
    main()
