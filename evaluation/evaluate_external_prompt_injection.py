from __future__ import annotations

from pathlib import Path
from typing import Any

from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

from backend.app.detection.hybrid_detector import detect_hybrid
from backend.app.detection.models import DetectionResult, DetectorType
from evaluation.external_datasets import (
    ExternalSample,
    load_deepset_prompt_injections,
    load_lakera_gandalf_ignore_instructions,
    load_protectai_prompt_injection_validation,
)


REPORT_PATH = Path("reports/external_prompt_injection_report.md")


DATASET_SOURCES = {
    "deepset/prompt-injections": {
        "source": "Hugging Face",
        "url": "https://huggingface.co/datasets/deepset/prompt-injections",
        "license": "cc-by-4.0",
        "role": "Main external benchmark",
    },
    "protectai/prompt-injection-validation": {
        "source": "Hugging Face",
        "url": "https://huggingface.co/datasets/protectai/prompt-injection-validation",
        "license": "Not specified in accessible dataset metadata",
        "role": "Additional large-scale validation",
    },
    "Lakera/gandalf_ignore_instructions": {
        "source": "Hugging Face",
        "url": "https://huggingface.co/datasets/Lakera/gandalf_ignore_instructions",
        "license": "Not specified in accessible dataset metadata",
        "role": "Attack-focused recall validation",
    },
}


def is_injection_result(result: Any) -> bool:
    if isinstance(result, bool):
        return result

    if isinstance(result, DetectionResult):
        return result.detector_type == DetectorType.INJECTION

    if isinstance(result, dict):
        if result.get("injection_detected") is True:
            return True

        reason_codes = result.get("reason_codes") or result.get("reasons") or []
        for reason in reason_codes:
            if _is_injection_reason(reason):
                return True

        if str(result.get("action", "")).upper() == "BLOCK":
            return True

    if isinstance(result, (list, tuple, set)):
        return any(is_injection_result(item) for item in result)

    if getattr(result, "injection_detected", False) is True:
        return True

    for attr_name in ("reason_codes", "reasons"):
        reason_codes = getattr(result, attr_name, None)
        if reason_codes and any(_is_injection_reason(reason) for reason in reason_codes):
            return True

    detections = getattr(result, "detections", None)
    if detections is not None:
        return any(is_injection_result(item) for item in detections)

    return False


def _is_injection_reason(reason: Any) -> bool:
    reason_text = str(reason).upper()
    return (
        "INJ" in reason_text
        or "INJECTION" in reason_text
        or "JAILBREAK" in reason_text
        or "SYSTEM_PROMPT" in reason_text
    )


def detect_with_project_detector(text: str) -> bool:
    return is_injection_result(detect_hybrid(text))


def evaluate_samples(samples: list[ExternalSample]) -> dict[str, object]:
    y_true: list[bool] = []
    y_pred: list[bool] = []

    for sample in samples:
        y_true.append(sample.expected_injection)
        y_pred.append(detect_with_project_detector(sample.text))

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="binary",
        zero_division=0,
    )

    accuracy = accuracy_score(y_true, y_pred)

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[False, True]).ravel()
    positive_only = bool(y_true) and all(y_true)

    return {
        "size": len(samples),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "accuracy": round(float(accuracy), 4),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
        "positive_only": positive_only,
    }


def _format_metric(metric: dict[str, object], key: str) -> str:
    if metric.get("positive_only") and key in {"precision", "f1"}:
        return "N/A"
    return f"{float(metric[key]):.4f}"


def _format_count(metric: dict[str, object], key: str) -> str:
    if metric.get("positive_only") and key in {"fp", "tn"}:
        return "N/A"
    return str(metric[key])


def render_report(results: dict[str, dict[str, object]]) -> str:
    lines: list[str] = []

    lines.append("# External Prompt Injection Evaluation Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Dataset | Size | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for dataset_name, metric in results.items():
        lines.append(
            f"| {dataset_name} "
            f"| {metric['size']} "
            f"| {_format_metric(metric, 'precision')} "
            f"| {_format_metric(metric, 'recall')} "
            f"| {_format_metric(metric, 'f1')} "
            f"| {_format_metric(metric, 'accuracy')} "
            f"| {_format_count(metric, 'tp')} "
            f"| {_format_count(metric, 'fp')} "
            f"| {_format_count(metric, 'tn')} "
            f"| {_format_count(metric, 'fn')} |"
        )

    lines.append("")
    lines.append("## Dataset Sources")
    lines.append("")
    lines.append("| Dataset | Source | License | Role |")
    lines.append("|---|---|---|---|")
    for dataset_name, metadata in DATASET_SOURCES.items():
        lines.append(
            f"| `{dataset_name}` "
            f"| [{metadata['source']}]({metadata['url']}) "
            f"| {metadata['license']} "
            f"| {metadata['role']} |"
        )

    lines.append("")
    lines.append("## Experiment Roles")
    lines.append("")
    lines.append("| Experiment | Dataset | Purpose |")
    lines.append("|---|---|---|")
    lines.append("| Experiment A | `deepset/prompt-injections` | Main external Prompt Injection benchmark |")
    lines.append("| Experiment B | `protectai/prompt-injection-validation` | Larger additional validation set |")
    lines.append("| Experiment C | `Lakera/gandalf_ignore_instructions` | Attack-focused recall validation |")
    lines.append("| Experiment D | Internal Korean public-sector scenario dataset | Project-specific regression and public-sector scenario validation |")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- `deepset/prompt-injections` is used as the main external benchmark dataset because it includes both legitimate and injection prompts.")
    lines.append("- `protectai/prompt-injection-validation` is used as an additional larger validation dataset. If the original Hugging Face repo requires authentication in the execution environment, the script falls back to an accessible mirror with the same 3,227-row split structure.")
    lines.append("- `Lakera/gandalf_ignore_instructions` is attack-focused, so precision and F1 are marked as `N/A`; its result should be interpreted mainly as recall-oriented validation.")
    lines.append("- The previous 24-sample external validation set is retained only as a preliminary validation sample and is not used as the main paper-level performance comparison.")
    lines.append("- Dataset contents are loaded from Hugging Face at runtime and are not committed to this repository.")
    lines.append("")
    lines.append("## Paper Wording")
    lines.append("")
    lines.append("기존 외부 검증 데이터셋 24건은 표본 수가 작아 예비 검증 자료로만 활용하였다. 교수 피드백을 반영하여 본 실험에서는 Hugging Face 공개 데이터셋인 `deepset/prompt-injections`, `protectai/prompt-injection-validation`, `Lakera/gandalf_ignore_instructions`를 추가하였다. 이를 통해 Prompt Injection 탐지 성능을 Precision, Recall, F1-score, Accuracy 기준으로 정량 평가하였다.")
    lines.append("")
    lines.append("특히 `deepset/prompt-injections`는 정상 프롬프트와 공격 프롬프트를 모두 포함하므로 본 프로젝트의 메인 외부 성능 비교 데이터셋으로 사용하였다. `protectai/prompt-injection-validation`은 더 큰 규모의 추가 검증셋으로 사용하였고, `Lakera/gandalf_ignore_instructions`는 \"ignore previous instructions\" 계열 공격 탐지력을 확인하기 위한 공격 특화 Recall 검증셋으로 사용하였다.")
    lines.append("")
    lines.append("기준 논문의 평가 관점을 참고하여 공개 데이터셋 기반 정량 평가를 수행하였다. 데이터셋과 평가 방식이 다르므로 기준 논문과 직접적인 수치 우열 비교는 하지 않는다.")

    return "\n".join(lines)


def main() -> None:
    datasets = {
        "deepset/prompt-injections": load_deepset_prompt_injections(),
        "protectai/prompt-injection-validation": load_protectai_prompt_injection_validation(),
        "Lakera/gandalf_ignore_instructions": load_lakera_gandalf_ignore_instructions(),
    }

    results = {
        dataset_name: evaluate_samples(samples)
        for dataset_name, samples in datasets.items()
    }

    report = render_report(results)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print(report)


if __name__ == "__main__":
    main()
