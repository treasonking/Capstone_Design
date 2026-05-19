from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib  # noqa: E402

from backend.app.detection.lightweight_classifier import LightweightClassifier  # noqa: E402
from evaluation.external_dataset_compare import (  # noqa: E402
    DEFAULT_EVAL_PATH,
    DATASET_SPECS,
    DatasetBundle,
    _classifier_from_model_dir,
    _evaluate_dataset,
    _fmt,
    _load_eval_path,
)
from evaluation.external_datasets import load_deepset_prompt_injections  # noqa: E402
from tools.train_lightweight_classifier import (  # noqa: E402
    DEFAULT_DATASETS,
    INJECTION_LABEL,
    SAFE_LABEL,
    _classifier,
    _collect_samples,
    _vectorizer,
)


REPORT_PATH = Path("reports/deepset_official_split_report.md")
RESULTS_JSON_PATH = Path("reports/deepset_official_split_results.json")


def _deepset_spec():
    for spec in DATASET_SPECS:
        if spec.name == "deepset/prompt-injections":
            return spec
    raise RuntimeError("deepset spec not found")


def _train_deepset_official_classifier(output_dir: Path, threshold: float) -> LightweightClassifier:
    samples = _collect_samples(DEFAULT_DATASETS)
    seen = set(samples)
    for row in load_deepset_prompt_injections("train"):
        label = INJECTION_LABEL if row.expected_injection else SAFE_LABEL
        sample = (row.text.strip(), label)
        if not sample[0] or sample in seen:
            continue
        seen.add(sample)
        samples.append(sample)

    texts = [text for text, _label in samples]
    labels = [label for _text, label in samples]
    vectorizer = _vectorizer()
    estimator = _classifier()
    features = vectorizer.fit_transform(texts)
    estimator.fit(features, labels)

    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(vectorizer, output_dir / "vectorizer.joblib")
    joblib.dump(estimator, output_dir / "classifier.joblib")
    (output_dir / "model_metadata.json").write_text(
        json.dumps(
            {
                "model_version": "deepset-official-train",
                "training_data": "internal Korean scenarios + deepset official train split",
                "training_sources": [
                    "internal_korean_scenarios",
                    "deepset/prompt-injections official train split",
                ],
                "note": "Temporary artifact for deepset official split evaluation.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return LightweightClassifier(
        vectorizer_path=output_dir / "vectorizer.joblib",
        classifier_path=output_dir / "classifier.joblib",
        threshold=threshold,
    )


def _deepset_custom_bundle(eval_path: Path):
    for bundle in _load_eval_path(eval_path, None):
        if bundle.spec.name == "deepset/prompt-injections":
            return bundle
    raise RuntimeError("deepset custom eval bundle not found")


def _deepset_official_bundle():
    spec = _deepset_spec()
    return DatasetBundle(
        spec=spec,
        samples=load_deepset_prompt_injections("test"),
        status="loaded",
        note="Loaded from deepset official test split.",
    )


def _with_policy(rows: list[dict[str, Any]], split_policy: str) -> list[dict[str, Any]]:
    return [{**row, "split_policy": split_policy} for row in rows]


def _evaluate(threshold: float, custom_eval_path: Path, custom_model_dir: Path) -> list[dict[str, Any]]:
    custom_classifier = _classifier_from_model_dir(custom_model_dir, threshold)
    custom_rows = _evaluate_dataset(
        dataset=_deepset_custom_bundle(custom_eval_path),
        classifier=custom_classifier,
        classifier_status=custom_classifier.status(),
        threshold=threshold,
        model_version="external-tuned",
    )

    with tempfile.TemporaryDirectory(prefix="deepset-official-model-") as tmp:
        official_classifier = _train_deepset_official_classifier(Path(tmp), threshold)
        official_rows = _evaluate_dataset(
            dataset=_deepset_official_bundle(),
            classifier=official_classifier,
            classifier_status=official_classifier.status(),
            threshold=threshold,
            model_version="deepset-official-train",
        )

    return [
        *_with_policy(custom_rows, "custom 70/30 eval"),
        *_with_policy(official_rows, "official train/test"),
    ]


def _render_report(generated_at: str, threshold: float, rows: list[dict[str, Any]]) -> str:
    hybrid_rows = {
        row["split_policy"]: row
        for row in rows
        if row["mode"] == "Hybrid / Full Pipeline"
    }
    custom_recall = hybrid_rows.get("custom 70/30 eval", {}).get("recall")
    official_recall = hybrid_rows.get("official train/test", {}).get("recall")
    if custom_recall is not None and official_recall is not None and official_recall >= custom_recall:
        conclusion = (
            "Official test split performance did not drop below the custom split result. "
            "This supports that the deepset improvement is not explained solely by the custom 70/30 split, "
            "although near-duplicate findings still require cautious wording."
        )
    elif custom_recall is not None and official_recall is not None:
        conclusion = (
            "Official test split performance is lower than the custom split result. "
            "Prefer official split numbers when making claims about deepset generalization."
        )
    else:
        conclusion = "One or more split policies were unavailable; interpret deepset comparison cautiously."

    lines = [
        "# Deepset Official Split Comparison",
        "",
        f"- Generated at: `{generated_at}`",
        f"- Lightweight threshold: `{threshold:.2f}`",
        "",
        "| Split Policy | Dataset | Model Version | Mode | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['split_policy']} "
            f"| `{row['dataset_name']}` "
            f"| {row['model_version']} "
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
            "## Interpretation",
            "",
            conclusion,
            "",
            "- `custom 70/30 eval` uses the project-generated held-out eval split and the saved `external-tuned` artifact.",
            "- `official train/test` trains a temporary lightweight model with internal samples plus deepset official train split, then evaluates deepset official test split.",
            "- If custom split performance is much higher than official test performance, custom split metrics may be easier or inflated by similar examples.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(generated_at: str, threshold: float, rows: list[dict[str, Any]], path: Path) -> None:
    payload = {
        "generated_at": generated_at,
        "threshold": threshold,
        "results": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare deepset custom split and official train/test split.")
    parser.add_argument("--threshold", type=float, default=0.30, help="Lightweight model threshold.")
    parser.add_argument("--eval-path", default=str(DEFAULT_EVAL_PATH), help="Custom held-out eval JSONL path.")
    parser.add_argument("--model-dir", default="models/lightweight_external_tuned", help="Custom external-tuned model dir.")
    parser.add_argument("--report", default=str(REPORT_PATH), help="Markdown report output path.")
    parser.add_argument("--json", default=str(RESULTS_JSON_PATH), help="JSON result output path.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    rows = _evaluate(
        threshold=args.threshold,
        custom_eval_path=Path(args.eval_path),
        custom_model_dir=Path(args.model_dir),
    )
    generated_at = datetime.now().isoformat(timespec="seconds")
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_report(generated_at, args.threshold, rows), encoding="utf-8")
    _write_json(generated_at, args.threshold, rows, Path(args.json))
    print(f"Deepset official split report saved to: {args.report}")
    print(f"Deepset official split JSON saved to: {args.json}")


if __name__ == "__main__":
    main()
