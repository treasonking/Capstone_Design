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

from evaluation.external_dataset_compare import (
    DATASET_SPECS,
    DEFAULT_EVAL_PATH,
    _apply_model_version_override,
    _classifier_from_model_dir,
    _fmt,
    _hybrid_pipeline,
    _load_dataset,
    _load_eval_path,
    _metric_result,
    _model_metadata,
    _model_only,
    _optional_limit,
    _runtime_versions,
)


OPTIMIZER_REPORT_PATH = Path("reports/external_threshold_optimizer_report.md")
OPTIMIZER_JSON_PATH = Path("reports/external_threshold_optimizer_results.json")
OPTIMIZER_CSV_PATH = Path("reports/external_threshold_optimizer_results.csv")
DEFAULT_THRESHOLDS = "0.30,0.35,0.40,0.45,0.50,0.55,0.60,0.65,0.70"


def _parse_thresholds(raw: str) -> list[float]:
    thresholds: list[float] = []
    for item in raw.split(","):
        stripped = item.strip()
        if not stripped:
            continue
        value = float(stripped)
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Threshold must be between 0 and 1: {value}")
        thresholds.append(round(value, 4))
    if not thresholds:
        raise ValueError("At least one threshold candidate is required.")
    return sorted(dict.fromkeys(thresholds))


def _fp_rate(row: dict[str, Any]) -> float | None:
    fp = row.get("fp")
    tn = row.get("tn")
    if fp is None or tn is None:
        return None
    denominator = int(fp) + int(tn)
    return float(fp) / denominator if denominator else 0.0


def _score_key(row: dict[str, Any]) -> tuple[float, float, float, float]:
    fp_rate = row.get("fp_rate")
    precision = row.get("precision")
    recall = row.get("recall")
    f1 = row.get("f1")

    if f1 is None:
        return (
            float(recall or 0.0),
            float(precision or 0.0),
            -float(fp_rate or 0.0),
            -float(row["threshold"]),
        )

    precision_bonus = 1.0 if precision is not None and precision >= 0.70 else 0.0
    return (
        float(f1 or 0.0),
        precision_bonus,
        float(recall or 0.0),
        -float(fp_rate or 0.0),
    )


def _recommend_reason(row: dict[str, Any]) -> str:
    if row.get("f1") is None:
        return "positive-only dataset; recall-oriented recommendation"
    if row.get("precision") is not None and row["precision"] >= 0.70:
        return "best F1 with precision >= 0.70 preference"
    return "best F1 candidate; precision target not met"


def _mark_recommendations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["dataset_name"], row["mode"]), []).append(row)

    for candidates in grouped.values():
        valid = [
            row
            for row in candidates
            if row.get("recall") is not None and row.get("precision") is not None or row.get("positive_only")
        ]
        if not valid:
            continue
        recommended = max(valid, key=_score_key)
        recommended["recommended"] = True
        recommended["recommendation_reason"] = _recommend_reason(recommended)

    for row in rows:
        row.setdefault("recommended", False)
        row.setdefault("recommendation_reason", "")
    return rows


def _load_split_summary(eval_path: Path | None) -> dict[str, Any] | None:
    if eval_path is None:
        return None
    summary_path = eval_path.parent / "split_summary.json"
    if not summary_path.exists():
        return None
    try:
        return json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _evaluate(
    *,
    thresholds: list[float],
    split: str,
    eval_path: Path | None,
    model_dir: Path | None,
    model_version_override: str | None,
    max_samples: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    classifier = _classifier_from_model_dir(model_dir, thresholds[0])
    classifier_status = classifier.status()
    model_metadata = _apply_model_version_override(
        _model_metadata(classifier_status),
        model_version_override,
    )
    model_version = model_metadata["model_version"]
    datasets = (
        _load_eval_path(eval_path, max_samples)
        if eval_path is not None
        else [_load_dataset(spec, split, max_samples) for spec in DATASET_SPECS]
    )

    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        classifier.threshold = threshold
        for dataset in datasets:
            if dataset.status != "loaded" or not dataset.samples:
                for mode in ("Lightweight Model Only", "Hybrid / Full Pipeline"):
                    rows.append(
                        {
                            "dataset_name": dataset.spec.name,
                            "model_version": model_version,
                            "threshold": threshold,
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
                            "fp_rate": None,
                            "latency_ms_avg": None,
                            "model_status": classifier_status.status,
                            "dataset_status": dataset.status,
                            "note": dataset.note,
                        }
                    )
                continue

            if classifier_status.enabled:
                model_row = _metric_result(
                    dataset=dataset,
                    model_version=model_version,
                    mode="Lightweight Model Only",
                    predictor=_model_only(classifier),
                    model_status=classifier_status.status,
                )
                model_row["threshold"] = threshold
                model_row["fp_rate"] = _fp_rate(model_row)
                rows.append(model_row)

            hybrid_row = _metric_result(
                dataset=dataset,
                model_version=model_version,
                mode="Hybrid / Full Pipeline",
                predictor=_hybrid_pipeline(classifier, threshold),
                model_status=classifier_status.status,
            )
            hybrid_row["threshold"] = threshold
            hybrid_row["fp_rate"] = _fp_rate(hybrid_row)
            rows.append(hybrid_row)

    rows = _mark_recommendations(rows)
    recommendations = [row for row in rows if row["recommended"]]
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
        "split_summary": _load_split_summary(eval_path),
        "datasets": [
            {
                "name": dataset.spec.name,
                "samples": len(dataset.samples),
                "status": dataset.status,
                "note": dataset.note,
                "positive_only": dataset.spec.positive_only,
            }
            for dataset in datasets
        ],
        "recommendations": recommendations,
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
        "# External Threshold Optimizer",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Evaluation source: `{split}`",
        f"- Threshold candidates: `{', '.join(f'{item:.2f}' for item in thresholds)}`",
        f"- Model version: `{metadata['model_metadata']['model_version']}`",
        f"- Model status: `{metadata['classifier_status']['status']}`",
        "",
        "## Recommended Thresholds",
        "",
        "| Dataset | Model Version | Mode | Recommended Threshold | Precision | Recall | F1 | FP Rate | Reason |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in metadata["recommendations"]:
        lines.append(
            f"| `{row['dataset_name']}` "
            f"| {row['model_version']} "
            f"| {row['mode']} "
            f"| {_fmt(row['threshold'], 2)} "
            f"| {_fmt(row['precision'])} "
            f"| {_fmt(row['recall'])} "
            f"| {_fmt(row['f1'])} "
            f"| {_fmt(row['fp_rate'])} "
            f"| {row['recommendation_reason']} |"
        )

    split_summary = metadata.get("split_summary")
    if split_summary:
        lines.extend(
            [
                "",
                "## Data Leakage Control",
                "",
                f"- External datasets were split with random seed `{split_summary.get('random_seed')}`.",
                f"- Train/eval id overlap: `{split_summary.get('train_eval_overlap')}`.",
                f"- Train size: `{split_summary.get('train_size')}`, eval size: `{split_summary.get('eval_size')}`.",
            ]
        )

    lines.extend(
        [
            "",
            "## Results",
            "",
            "| Dataset | Model Version | Threshold | Mode | Precision | Recall | F1 | FP Rate | Recommended |",
            "|---|---|---:|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| `{row['dataset_name']}` "
            f"| {row['model_version']} "
            f"| {_fmt(row['threshold'], 2)} "
            f"| {row['mode']} "
            f"| {_fmt(row['precision'])} "
            f"| {_fmt(row['recall'])} "
            f"| {_fmt(row['f1'])} "
            f"| {_fmt(row['fp_rate'])} "
            f"| {'yes' if row['recommended'] else ''} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- F1이 계산 가능한 데이터셋은 F1을 우선하고, Precision 0.70 이상 후보를 선호한다.",
            "- positive-only 데이터셋은 안전 negative가 없어 FP rate와 F1을 계산할 수 없으므로 Recall 중심으로만 추천한다.",
            "- 추천 threshold는 운영 정책에 바로 고정하기보다 held-out eval 결과와 FP 증가 여부를 함께 검토하는 후보값이다.",
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
        "model_version",
        "threshold",
        "mode",
        "precision",
        "recall",
        "f1",
        "fp_rate",
        "recommended",
        "recommendation_reason",
        "accuracy",
        "tp",
        "fp",
        "tn",
        "fn",
        "size",
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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select lightweight model thresholds using held-out external prompt injection eval data."
    )
    parser.add_argument("--thresholds", default=DEFAULT_THRESHOLDS, help="Comma-separated threshold candidates.")
    parser.add_argument("--split", default="all", help="Hugging Face split to load when --eval-path is not used.")
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
    parser.add_argument("--model-version", default="", help="Model version label to record in result rows.")
    parser.add_argument("--max-samples", type=int, default=-1, help="Sample cap per dataset. -1 means full dataset.")
    parser.add_argument("--report", default=str(OPTIMIZER_REPORT_PATH), help="Markdown report output path.")
    parser.add_argument("--json", default=str(OPTIMIZER_JSON_PATH), help="JSON output path.")
    parser.add_argument("--csv", default=str(OPTIMIZER_CSV_PATH), help="CSV output path.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    thresholds = _parse_thresholds(args.thresholds)
    eval_path = Path(args.eval_path) if args.eval_path else None
    rows, metadata = _evaluate(
        thresholds=thresholds,
        split=args.split,
        eval_path=eval_path,
        model_dir=Path(args.model_dir) if args.model_dir else None,
        model_version_override=args.model_version or None,
        max_samples=_optional_limit(args.max_samples),
    )
    generated_at = datetime.now().isoformat(timespec="seconds")
    split_label = str(eval_path) if eval_path is not None else args.split
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _render_report(
            generated_at=generated_at,
            split=split_label,
            thresholds=thresholds,
            rows=rows,
            metadata=metadata,
        ),
        encoding="utf-8",
    )
    _write_json(
        generated_at=generated_at,
        split=split_label,
        thresholds=thresholds,
        rows=rows,
        metadata=metadata,
        path=Path(args.json),
    )
    _write_csv(rows, Path(args.csv))
    print(f"External threshold optimizer report saved to: {args.report}")
    print(f"External threshold optimizer JSON saved to: {args.json}")
    print(f"External threshold optimizer CSV saved to: {args.csv}")


if __name__ == "__main__":
    main()
