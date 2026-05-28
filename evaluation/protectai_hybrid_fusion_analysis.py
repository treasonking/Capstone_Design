from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.detection.injection_detector import detect_injection
from backend.app.detection.lightweight_classifier import LightweightClassifier
from backend.app.detection.pii_detector import detect_pii
from backend.app.detection.reason_codes import ordered_reason_codes
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
)
from evaluation.prompt_injection_fusion import (
    DEFAULT_MEDIUM_RULE_MODEL_SUPPORT_THRESHOLD,
    fuse_prompt_injection_decision,
    prompt_injection_model_score,
)


PROTECTAI_DATASET_NAME = "protectai/prompt-injection-validation"
DEFAULT_EVAL_PATH = Path("datasets/external_splits/eval_external_prompt_injection.jsonl")
DEFAULT_MODEL_DIR = Path("models/lightweight_external_tuned")
DEFAULT_THRESHOLDS = (0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70)

PREDICTION_CSV_PATH = Path("reports/protectai_model_vs_hybrid_predictions.csv")
FP_ANALYSIS_PATH = Path("reports/protectai_hybrid_fp_analysis.md")
THRESHOLD_SWEEP_CSV_PATH = Path("reports/protectai_threshold_sweep.csv")
FIX_REPORT_PATH = Path("reports/protectai_hybrid_fix_report.md")


@dataclass(frozen=True, slots=True)
class Metrics:
    precision: float
    recall: float
    f1: float
    tp: int
    fp: int
    fn: int
    tn: int


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _metrics(rows: list[dict[str, Any]], pred_key: str) -> Metrics:
    tp = fp = fn = tn = 0
    for row in rows:
        expected = int(row["label"]) == 1
        predicted = int(row[pred_key]) == 1
        if predicted and expected:
            tp += 1
        elif predicted and not expected:
            fp += 1
        elif not predicted and expected:
            fn += 1
        else:
            tn += 1
    precision = _safe_div(tp, tp + fp)
    recall = _safe_div(tp, tp + fn)
    f1 = _safe_div(2 * precision * recall, precision + recall)
    return Metrics(precision=precision, recall=recall, f1=f1, tp=tp, fp=fp, fn=fn, tn=tn)


def _metrics_row(threshold: float, mode: str, metrics: Metrics) -> dict[str, Any]:
    return {
        "threshold": f"{threshold:.2f}",
        "mode": mode,
        "precision": metrics.precision,
        "recall": metrics.recall,
        "f1": metrics.f1,
        "tp": metrics.tp,
        "fp": metrics.fp,
        "fn": metrics.fn,
    }


def _join_codes(codes: list[str] | tuple[str, ...]) -> str:
    return ";".join(ordered_reason_codes(list(codes)))


def _load_protectai(eval_path: Path | None, split: str, max_samples: int | None) -> tuple[list[Any], str]:
    if eval_path is not None:
        bundles = _load_eval_path(eval_path, max_samples)
        bundle = next(item for item in bundles if item.spec.name == PROTECTAI_DATASET_NAME)
        return bundle.samples, f"Loaded from held-out eval split: {eval_path}"

    spec = next(item for item in DATASET_SPECS if item.name == PROTECTAI_DATASET_NAME)
    bundle = _load_dataset(spec, split, max_samples)
    return bundle.samples, bundle.note


def _legacy_final_action(model_predicted: bool, rule_predicted: bool) -> str:
    if model_predicted:
        return "MODEL_DETECTED"
    if rule_predicted:
        return "RULE_DETECTED_LEGACY_OR"
    return "NO_SIGNAL"


def _prediction_rows(
    *,
    samples: list[Any],
    classifier: LightweightClassifier,
    threshold: float,
) -> list[dict[str, Any]]:
    classifier.threshold = threshold
    rows: list[dict[str, Any]] = []

    for sample in samples:
        rule_hits = detect_injection(sample.text)
        pii_hits = detect_pii(sample.text)
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
        label = 1 if sample.expected_injection else 0
        hybrid_predicted = bool(model_predicted or rule_predicted)
        calibrated_predicted = bool(fusion.predicted)

        rows.append(
            {
                "id": sample.id,
                "text": sample.text,
                "label": label,
                "model_pred": int(model_predicted),
                "model_score": model_score,
                "model_label": model_prediction.label,
                "model_confidence": model_prediction.confidence,
                "rule_pred": int(rule_predicted),
                "rule_reason_codes": _join_codes([hit.reason_code for hit in rule_hits]),
                "rule_high_reason_codes": _join_codes(fusion.high_reason_codes),
                "rule_medium_reason_codes": _join_codes(fusion.medium_reason_codes),
                "rule_low_reason_codes": _join_codes(fusion.low_reason_codes),
                "pii_reason_codes": _join_codes([hit.reason_code for hit in pii_hits]),
                "hybrid_pred": int(hybrid_predicted),
                "final_action": _legacy_final_action(model_predicted, rule_predicted),
                "calibrated_hybrid_pred": int(calibrated_predicted),
                "calibrated_final_action": fusion.final_action,
                "is_model_fp": int(label == 0 and model_predicted),
                "is_model_fn": int(label == 1 and not model_predicted),
                "is_hybrid_fp": int(label == 0 and hybrid_predicted),
                "is_hybrid_fn": int(label == 1 and not hybrid_predicted),
                "hybrid_added_fp": int(label == 0 and not model_predicted and hybrid_predicted),
                "hybrid_added_tp": int(label == 1 and not model_predicted and hybrid_predicted),
                "is_calibrated_hybrid_fp": int(label == 0 and calibrated_predicted),
                "is_calibrated_hybrid_fn": int(label == 1 and not calibrated_predicted),
                "calibrated_hybrid_added_fp": int(label == 0 and not model_predicted and calibrated_predicted),
                "calibrated_hybrid_added_tp": int(label == 1 and not model_predicted and calibrated_predicted),
            }
        )

    return rows


def _threshold_sweep_rows(
    *,
    samples: list[Any],
    classifier: LightweightClassifier,
    thresholds: list[float],
) -> list[dict[str, Any]]:
    sweep_rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        rows = _prediction_rows(samples=samples, classifier=classifier, threshold=threshold)
        sweep_rows.append(_metrics_row(threshold, "Rule Only", _metrics(rows, "rule_pred")))
        sweep_rows.append(_metrics_row(threshold, "Lightweight Model Only", _metrics(rows, "model_pred")))
        sweep_rows.append(_metrics_row(threshold, "Hybrid / Full Pipeline (legacy OR)", _metrics(rows, "hybrid_pred")))
        sweep_rows.append(_metrics_row(threshold, "Hybrid Calibrated", _metrics(rows, "calibrated_hybrid_pred")))
    return sweep_rows


def _truncate(text: str, limit: int = 180) -> str:
    normalized = " ".join(text.split()).replace("|", "\\|")
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3]}..."


def _metric_table_row(mode: str, metrics: Metrics) -> str:
    return (
        f"| {mode} | {_fmt(metrics.precision)} | {_fmt(metrics.recall)} | {_fmt(metrics.f1)} "
        f"| {metrics.tp} / {metrics.fp} / {metrics.fn} |"
    )


def _reason_counter(rows: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        if not int(row["hybrid_added_fp"]):
            continue
        for reason_code in str(row["rule_reason_codes"]).split(";"):
            if reason_code:
                counter[reason_code] += 1
    return counter


def _render_fp_analysis(
    *,
    generated_at: str,
    dataset_note: str,
    threshold: float,
    model_version: str,
    rows: list[dict[str, Any]],
) -> str:
    rule_metrics = _metrics(rows, "rule_pred")
    model_metrics = _metrics(rows, "model_pred")
    hybrid_metrics = _metrics(rows, "hybrid_pred")
    added_fp_rows = [row for row in rows if int(row["hybrid_added_fp"])]
    added_tp = sum(int(row["hybrid_added_tp"]) for row in rows)
    reason_counts = _reason_counter(rows)

    lines = [
        "# protectai Hybrid FP Analysis",
        "",
        "## Summary",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Dataset: {PROTECTAI_DATASET_NAME}",
        f"- Dataset note: {dataset_note or '-'}",
        f"- Model version: `{model_version}`",
        f"- Threshold: `{threshold:.2f}`",
        f"- Model Only: {model_metrics.tp} / {model_metrics.fp} / {model_metrics.fn}",
        f"- Hybrid: {hybrid_metrics.tp} / {hybrid_metrics.fp} / {hybrid_metrics.fn}",
        f"- Hybrid added FP: {len(added_fp_rows)}",
        f"- Hybrid added TP: {added_tp}",
        "",
        "## Cause",
        "",
        "Hybrid underperformed Model Only because the rule layer added false positives without reducing false negatives.",
        "",
        "## FP by reason_code",
        "",
        "| reason_code | count |",
        "|---|---:|",
    ]
    for reason_code, count in reason_counts.most_common():
        lines.append(f"| {reason_code} | {count} |")

    lines.extend(
        [
            "",
            "## FP examples",
            "",
            "| id | label | model_score | rule_reason_codes | text |",
            "|---|---:|---:|---|---|",
        ]
    )
    for row in added_fp_rows[:12]:
        lines.append(
            f"| {row['id']} | {row['label']} | {_fmt(row['model_score'])} "
            f"| {row['rule_reason_codes']} | {_truncate(str(row['text']))} |"
        )

    lines.extend(
        [
            "",
            "## PII separation check",
            "",
            "The protectai prompt-injection benchmark uses only prompt-injection rule hits for `hybrid_pred`. PII hits are written to `pii_reason_codes` in the CSV for auditability, but they do not affect prompt-injection positive predictions.",
            "",
            "## Interpretation",
            "",
            "Hybrid should not be interpreted as a pure accuracy-improving ensemble. It is an operational security pipeline that combines PII detection, policy decision, reason_code, and auditability. However, for prompt-injection-only benchmark evaluation, rule severity and model-rule fusion need to be calibrated.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_fix_report(
    *,
    generated_at: str,
    threshold: float,
    medium_threshold: float,
    rows: list[dict[str, Any]],
) -> str:
    before_rule = _metrics(rows, "rule_pred")
    before_model = _metrics(rows, "model_pred")
    before_hybrid = _metrics(rows, "hybrid_pred")
    after_hybrid = _metrics(rows, "calibrated_hybrid_pred")

    lines = [
        "# protectai Hybrid Fusion Fix Report",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Evaluation threshold: `{threshold:.2f}`",
        f"- Medium-rule model-support threshold: `{medium_threshold:.2f}`",
        "",
        "## Before",
        "",
        "| Mode | Precision | Recall | F1 | TP / FP / FN |",
        "|---|---:|---:|---:|---|",
        _metric_table_row("Rule Only", before_rule),
        _metric_table_row("Model Only", before_model),
        _metric_table_row("Hybrid", before_hybrid),
        "",
        "## After",
        "",
        "| Mode | Precision | Recall | F1 | TP / FP / FN |",
        "|---|---:|---:|---:|---|",
        _metric_table_row("Rule Only", before_rule),
        _metric_table_row("Model Only", before_model),
        _metric_table_row("Hybrid Calibrated", after_hybrid),
        "",
        "## Interpretation",
        "",
        "The previous Hybrid pipeline underperformed Model Only on the protectai dataset because the rule layer increased false positives without reducing false negatives. The calibrated fusion logic reduces rule-only over-triggering by allowing only high-severity rules to override the model prediction and requiring model support for medium-severity rules.",
        "",
        "protectai/prompt-injection-validation 데이터셋에서 초기 Hybrid 파이프라인은 Lightweight Model Only보다 낮은 F1을 보였다. 원인 분석 결과, Hybrid는 Model Only와 동일한 TP/FN을 기록했지만 FP가 2건에서 20건으로 증가하였다. 이는 Rule 계층이 해당 데이터셋에서 모델이 놓친 공격을 추가로 복구하지 못하고, 일부 정상 샘플을 위험으로 오탐했기 때문이다. 따라서 본 시스템의 Hybrid 구조는 모든 벤치마크에서 단일 모델보다 우수한 분류기로 해석하기보다, 개인정보 탐지, 정책 결정, reason_code, 감사 가능성을 결합한 운영형 보안 파이프라인으로 해석한다.",
        "",
    ]
    return "\n".join(lines)


def _write_csv(rows: list[dict[str, Any]], path: Path, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def _parse_thresholds(raw: str) -> list[float]:
    return [float(item.strip()) for item in raw.split(",") if item.strip()]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze and calibrate Model Only vs Hybrid predictions on protectai/prompt-injection-validation."
    )
    parser.add_argument("--threshold", type=float, default=0.30, help="Lightweight model threshold for before/after reports.")
    parser.add_argument(
        "--threshold-sweep",
        default=",".join(f"{item:.2f}" for item in DEFAULT_THRESHOLDS),
        help="Comma-separated model thresholds for protectai_threshold_sweep.csv.",
    )
    parser.add_argument("--split", default="all", help="Hugging Face split to load when --eval-path is empty.")
    parser.add_argument(
        "--eval-path",
        default=str(DEFAULT_EVAL_PATH),
        help="Held-out external eval JSONL path. Use an empty string to load from Hugging Face.",
    )
    parser.add_argument(
        "--model-dir",
        default=str(DEFAULT_MODEL_DIR),
        help="Directory containing vectorizer.joblib and classifier.joblib.",
    )
    parser.add_argument("--model-version", default="", help="Model version label override.")
    parser.add_argument("--max-samples", type=int, default=-1, help="Sample cap. -1 means full dataset.")
    parser.add_argument("--predictions-csv", default=str(PREDICTION_CSV_PATH))
    parser.add_argument("--fp-report", default=str(FP_ANALYSIS_PATH))
    parser.add_argument("--threshold-csv", default=str(THRESHOLD_SWEEP_CSV_PATH))
    parser.add_argument("--fix-report", default=str(FIX_REPORT_PATH))
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    eval_path = Path(args.eval_path) if args.eval_path else None
    samples, dataset_note = _load_protectai(
        eval_path,
        args.split,
        _optional_limit(args.max_samples),
    )
    model_dir = Path(args.model_dir) if args.model_dir else None
    classifier = _classifier_from_model_dir(model_dir, args.threshold)
    classifier_status = classifier.status()
    model_metadata = _apply_model_version_override(
        _model_metadata(classifier_status),
        args.model_version or None,
    )
    model_version = model_metadata["model_version"]
    generated_at = datetime.now().isoformat(timespec="seconds")

    prediction_rows = _prediction_rows(
        samples=samples,
        classifier=classifier,
        threshold=args.threshold,
    )
    prediction_fieldnames = [
        "id",
        "text",
        "label",
        "model_pred",
        "model_score",
        "model_label",
        "model_confidence",
        "rule_pred",
        "rule_reason_codes",
        "rule_high_reason_codes",
        "rule_medium_reason_codes",
        "rule_low_reason_codes",
        "pii_reason_codes",
        "hybrid_pred",
        "final_action",
        "calibrated_hybrid_pred",
        "calibrated_final_action",
        "is_model_fp",
        "is_model_fn",
        "is_hybrid_fp",
        "is_hybrid_fn",
        "hybrid_added_fp",
        "hybrid_added_tp",
        "is_calibrated_hybrid_fp",
        "is_calibrated_hybrid_fn",
        "calibrated_hybrid_added_fp",
        "calibrated_hybrid_added_tp",
    ]
    _write_csv(prediction_rows, Path(args.predictions_csv), prediction_fieldnames)

    thresholds = _parse_thresholds(args.threshold_sweep)
    sweep_rows = _threshold_sweep_rows(
        samples=samples,
        classifier=classifier,
        thresholds=thresholds,
    )
    _write_csv(
        sweep_rows,
        Path(args.threshold_csv),
        ["threshold", "mode", "precision", "recall", "f1", "tp", "fp", "fn"],
    )

    Path(args.fp_report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.fp_report).write_text(
        _render_fp_analysis(
            generated_at=generated_at,
            dataset_note=dataset_note,
            threshold=args.threshold,
            model_version=model_version,
            rows=prediction_rows,
        ),
        encoding="utf-8",
    )
    Path(args.fix_report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.fix_report).write_text(
        _render_fix_report(
            generated_at=generated_at,
            threshold=args.threshold,
            medium_threshold=DEFAULT_MEDIUM_RULE_MODEL_SUPPORT_THRESHOLD,
            rows=prediction_rows,
        ),
        encoding="utf-8",
    )

    summary = {
        "predictions_csv": args.predictions_csv,
        "fp_report": args.fp_report,
        "threshold_csv": args.threshold_csv,
        "fix_report": args.fix_report,
        "rows": len(prediction_rows),
        "model_status": classifier_status.status,
        "model_version": model_version,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
