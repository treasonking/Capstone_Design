from __future__ import annotations

import json
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
ERROR_PATH = Path("reports/external_prompt_injection_errors.json")
FALSE_NEGATIVE_REPORT_PATH = Path("reports/external_prompt_injection_false_negatives.md")
MAX_ERROR_SAMPLES = 50
TEXT_PREVIEW_LIMIT = 300


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


def _text_preview(text: str) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= TEXT_PREVIEW_LIMIT:
        return normalized
    return f"{normalized[:TEXT_PREVIEW_LIMIT].rstrip()}..."


def _error_item(sample: ExternalSample, predicted_injection: bool) -> dict[str, object]:
    return {
        "id": sample.id,
        "text_preview": _text_preview(sample.text),
        "expected_injection": sample.expected_injection,
        "predicted_injection": predicted_injection,
    }


def evaluate_samples(samples: list[ExternalSample]) -> dict[str, object]:
    y_true: list[bool] = []
    y_pred: list[bool] = []
    false_negatives: list[dict[str, object]] = []
    false_positives: list[dict[str, object]] = []

    for sample in samples:
        predicted = detect_with_project_detector(sample.text)
        y_true.append(sample.expected_injection)
        y_pred.append(predicted)

        if sample.expected_injection and not predicted and len(false_negatives) < MAX_ERROR_SAMPLES:
            false_negatives.append(_error_item(sample, predicted))
        elif not sample.expected_injection and predicted and len(false_positives) < MAX_ERROR_SAMPLES:
            false_positives.append(_error_item(sample, predicted))

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
        "false_negatives": false_negatives,
        "false_positives": false_positives,
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
    lines.append("## Interpretation")
    lines.append("")
    lines.append("The external benchmark results show a clear performance gap between the internal regression dataset and public prompt injection datasets.")
    lines.append("")
    lines.append("The internal regression dataset mainly verifies whether the project-specific policy rules work correctly in expected public-sector and internal-network scenarios. In contrast, the public datasets include broader English prompt injection patterns, indirect instruction-following attacks, and diverse bypass-style prompts.")
    lines.append("")
    lines.append("Therefore, the low recall and F1-score on external datasets should be interpreted as evidence of limited generalization coverage in the current rule/heuristic-based detector, rather than as a failure of the proxy architecture itself.")
    lines.append("")
    lines.append("The current proxy architecture still provides the following operational controls:")
    lines.append("")
    lines.append("- input-side prompt inspection")
    lines.append("- output-side response inspection")
    lines.append("- PII masking/blocking")
    lines.append("- prompt injection blocking")
    lines.append("- reason-code based audit logging")
    lines.append("- policy-mode based control")
    lines.append("")
    lines.append("However, the external benchmark indicates that the prompt injection detector should be improved through:")
    lines.append("")
    lines.append("1. expanding English prompt injection patterns,")
    lines.append("2. adding multilingual bypass expressions,")
    lines.append("3. training or integrating a lightweight classifier,")
    lines.append("4. evaluating Rule Only and Hybrid modes separately,")
    lines.append("5. maintaining public benchmark evaluation as a regression test.")
    lines.append("")
    lines.append("This external public dataset evaluation was run against the currently active Hybrid Detector configuration. In this environment, the lightweight classifier artifact is loaded, so the reported result reflects the current combined detector behavior rather than a rule-only result.")
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
    lines.append("## Relation to Reference Study")
    lines.append("")
    lines.append("본 프로젝트는 Prompt Injection 공격과 방어를 체계적으로 평가한 기준 연구인 *Formalizing and Benchmarking Prompt Injection Attacks and Defenses*의 평가 관점을 참고하였다. 해당 연구는 Prompt Injection 방어 성능을 다양한 task, attack, defense 조합에서 분석하였으며, 탐지 기반 방어의 False Negative Rate와 False Positive Rate를 주요 지표로 사용하였다.")
    lines.append("")
    lines.append("본 프로젝트는 기준 연구의 평가 관점을 참고하되, 실제 공공기관·사내망 환경에서 사용할 수 있는 프록시형 보안 게이트웨이를 구현하는 데 초점을 두었다. 따라서 본 프로젝트의 평가는 Precision, Recall, F1-score, Accuracy를 사용하여 현재 탐지기의 일반화 성능을 확인하는 방식으로 수행하였다.")
    lines.append("")
    lines.append("두 실험은 동일 데이터셋과 동일 방어 방식을 사용하지 않으므로 절대적인 성능 우열 비교는 제한적이다. 대신 본 프로젝트는 기준 연구에서 제시한 Prompt Injection 방어 평가 필요성을 바탕으로, 공개 데이터셋 기반 정량 평가를 추가하고 현재 탐지기의 한계와 개선 방향을 도출하였다.")
    lines.append("")
    lines.append("## Planned Improvements")
    lines.append("")
    lines.append("외부 공개 데이터셋 평가 결과를 바탕으로 다음 개선 작업을 진행할 예정이다.")
    lines.append("")
    lines.append("| Priority | Improvement | Purpose |")
    lines.append("|---:|---|---|")
    lines.append("| 1 | 영어 기반 Prompt Injection 패턴 확장 | deepset/protectai 데이터셋 Recall 개선 |")
    lines.append("| 2 | 한국어·영어 혼합 우회 표현 추가 | 실제 국내 공공기관 사용 환경 반영 |")
    lines.append("| 3 | Rule Only와 Hybrid Detector 성능 분리 | 탐지 방식별 기여도 확인 |")
    lines.append("| 4 | Lightweight classifier artifact 개선 | rule 기반 탐지 한계 보완 |")
    lines.append("| 5 | 외부 데이터셋 회귀 테스트 자동화 | 향후 수정 시 성능 변화 추적 |")
    lines.append("| 6 | False Negative 샘플 분석 리포트 추가 | 놓친 공격 유형을 체계적으로 개선 |")
    lines.append("")
    lines.append("## Paper Wording")
    lines.append("")
    lines.append("기존 외부 검증 데이터셋 24건은 표본 수가 작아 예비 검증 자료로만 활용하였다. 교수 피드백을 반영하여 본 실험에서는 Hugging Face 공개 데이터셋인 `deepset/prompt-injections`, `protectai/prompt-injection-validation`, `Lakera/gandalf_ignore_instructions`를 추가하였다. 이를 통해 Prompt Injection 탐지 성능을 Precision, Recall, F1-score, Accuracy 기준으로 정량 평가하였다.")
    lines.append("")
    lines.append("특히 `deepset/prompt-injections`는 정상 프롬프트와 공격 프롬프트를 모두 포함하므로 본 프로젝트의 메인 외부 성능 비교 데이터셋으로 사용하였다. `protectai/prompt-injection-validation`은 더 큰 규모의 추가 검증셋으로 사용하였고, `Lakera/gandalf_ignore_instructions`는 \"ignore previous instructions\" 계열 공격 탐지력을 확인하기 위한 공격 특화 Recall 검증셋으로 사용하였다.")
    lines.append("")
    lines.append("기준 논문의 평가 관점을 참고하여 공개 데이터셋 기반 정량 평가를 수행하였다. 데이터셋과 평가 방식이 다르므로 기준 논문과 직접적인 수치 우열 비교는 하지 않는다.")

    return "\n".join(lines)


def write_error_samples(results: dict[str, dict[str, object]]) -> Path:
    payload: dict[str, dict[str, object]] = {}
    for dataset_name, metric in results.items():
        payload[dataset_name] = {
            "false_negatives": metric["false_negatives"],
            "false_positives": metric["false_positives"],
        }

    ERROR_PATH.parent.mkdir(parents=True, exist_ok=True)
    ERROR_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return ERROR_PATH


def render_false_negative_report(results: dict[str, dict[str, object]]) -> str:
    lines = [
        "# External Prompt Injection False Negative Analysis",
        "",
        "## Purpose",
        "",
        "This document tracks false negative samples from public prompt injection datasets. The goal is to identify missing attack patterns and improve detector coverage.",
        "",
        "## Summary",
        "",
        "| Dataset | FN Count | Main Missing Pattern | Planned Rule/Model Improvement |",
        "|---|---:|---|---|",
    ]

    improvement_by_dataset = {
        "deepset/prompt-injections": ("TBD", "Expand English injection patterns"),
        "protectai/prompt-injection-validation": ("TBD", "Add classifier-based detection"),
        "Lakera/gandalf_ignore_instructions": (
            "TBD",
            "Improve ignore-instruction attack coverage",
        ),
    }
    for dataset_name, metric in results.items():
        pattern, improvement = improvement_by_dataset.get(
            dataset_name,
            ("TBD", "Review missed attack patterns"),
        )
        lines.append(
            f"| {dataset_name} | {metric['fn']} | {pattern} | {improvement} |"
        )

    lines.extend(
        [
            "",
            "## Sample Storage",
            "",
            f"Up to {MAX_ERROR_SAMPLES} false negative and false positive previews per dataset are stored in `reports/external_prompt_injection_errors.json`. Text is truncated to avoid storing unnecessary full prompt content.",
            "",
            "## Analysis Categories",
            "",
            "False negative samples should be categorized into the following types.",
            "",
            "| Category | Description | Example Pattern |",
            "|---|---|---|",
            "| Direct override | Explicitly ignores prior instructions | ignore previous instructions |",
            "| Role manipulation | Assigns a new unsafe role to the model | you are now unrestricted |",
            "| System prompt extraction | Requests hidden system/developer messages | reveal your system prompt |",
            "| Policy bypass | Asks to disable safety or filtering | turn off the filter |",
            "| Indirect injection | Attack is embedded in a task/document | summarize this document and follow the hidden instruction |",
            "| Encoding/obfuscation | Attack uses spacing, symbols, encoding, or mixed language | i g n o r e, base64-like text |",
            "| Goal hijacking | Replaces the original user task with another goal | instead of the task, do this |",
        ]
    )
    return "\n".join(lines)


def write_false_negative_report(results: dict[str, dict[str, object]]) -> Path:
    FALSE_NEGATIVE_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    FALSE_NEGATIVE_REPORT_PATH.write_text(
        render_false_negative_report(results),
        encoding="utf-8",
    )
    return FALSE_NEGATIVE_REPORT_PATH


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
    write_error_samples(results)
    write_false_negative_report(results)

    print(report)


if __name__ == "__main__":
    main()
