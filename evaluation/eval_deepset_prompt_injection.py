from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from datasets import load_dataset
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)


DEFAULT_PROXY_URL = "http://127.0.0.1:8000/v1/chat/completions"
DEFAULT_DATASET_NAME = "deepset/prompt-injections"
DEFAULT_SPLIT = "train"
DEFAULT_MAX_SAMPLES = 100

RESULT_DIR = Path("evaluation/results")
REPORT_DIR = Path("reports")
RESULT_COLUMNS = [
    "id",
    "dataset",
    "split",
    "text",
    "true_label",
    "pred_label",
    "action",
    "reason_code",
    "reasons",
    "status_code",
    "error",
]


def ensure_dirs() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def load_prompt_injection_dataset(dataset_name: str, split: str):
    dataset_dict = load_dataset(dataset_name)

    if split not in dataset_dict:
        available = list(dataset_dict.keys())
        raise ValueError(
            f"Split '{split}' not found. Available splits: {available}"
        )

    dataset = dataset_dict[split]

    required_columns = {"text", "label"}
    actual_columns = set(dataset.column_names)

    missing = required_columns - actual_columns
    if missing:
        raise ValueError(
            f"Dataset is missing required columns: {missing}. "
            f"Actual columns: {dataset.column_names}"
        )

    return dataset


def build_payload(text: str, model: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": text,
            }
        ],
    }


def classify_proxy_response(response_json: dict[str, Any]) -> int:
    action = response_json.get("action")

    if action == "BLOCK":
        return 1

    return 0


def request_proxy(
    proxy_url: str,
    text: str,
    model: str,
    timeout: int,
) -> tuple[int, dict[str, Any], int | None, str | None]:
    payload = build_payload(text=text, model=model)

    try:
        response = requests.post(proxy_url, json=payload, timeout=timeout)
        status_code = response.status_code

        try:
            response_json = response.json()
        except ValueError as exc:
            return -1, {}, status_code, f"JSON_DECODE_ERROR: {exc}"

        if status_code >= 400:
            return -1, response_json, status_code, f"HTTP_ERROR: {status_code}"

        pred_label = classify_proxy_response(response_json)
        return pred_label, response_json, status_code, None

    except requests.RequestException as exc:
        return -1, {}, None, f"REQUEST_ERROR: {exc}"


def evaluate(
    proxy_url: str,
    dataset_name: str,
    split: str,
    max_samples: int,
    model: str,
    timeout: int,
) -> pd.DataFrame:
    dataset = load_prompt_injection_dataset(dataset_name, split)

    rows: list[dict[str, Any]] = []

    total = min(max(max_samples, 0), len(dataset))

    for idx in range(total):
        sample = dataset[idx]

        text = str(sample["text"])
        true_label = int(sample["label"])

        pred_label, response_json, status_code, error = request_proxy(
            proxy_url=proxy_url,
            text=text,
            model=model,
            timeout=timeout,
        )

        action = response_json.get("action") if response_json else None
        reason_code = response_json.get("reason_code") if response_json else None
        reasons = response_json.get("reasons") if response_json else None

        rows.append(
            {
                "id": idx,
                "dataset": dataset_name,
                "split": split,
                "text": text,
                "true_label": true_label,
                "pred_label": pred_label,
                "action": action,
                "reason_code": reason_code,
                "reasons": json.dumps(reasons, ensure_ascii=False)
                if reasons is not None
                else None,
                "status_code": status_code,
                "error": error,
            }
        )

    return pd.DataFrame(rows, columns=RESULT_COLUMNS)


def calculate_metrics(df: pd.DataFrame) -> dict[str, Any]:
    valid_df = df[df["pred_label"] != -1].copy()

    if valid_df.empty:
        return {
            "valid_samples": 0,
            "accuracy": 0.0,
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "tn": 0,
            "fp": 0,
            "fn": 0,
            "tp": 0,
        }

    y_true = valid_df["true_label"]
    y_pred = valid_df["pred_label"]

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="binary",
        zero_division=0,
    )

    accuracy = accuracy_score(y_true, y_pred)

    labels = [0, 1]
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    tn, fp, fn, tp = cm.ravel()

    return {
        "valid_samples": int(len(valid_df)),
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def save_results(df: pd.DataFrame) -> tuple[Path, Path, Path]:
    result_path = RESULT_DIR / "deepset_prompt_injection_results.csv"
    fn_path = RESULT_DIR / "deepset_prompt_injection_false_negatives.csv"
    fp_path = RESULT_DIR / "deepset_prompt_injection_false_positives.csv"

    df.to_csv(result_path, index=False, encoding="utf-8-sig")

    false_negatives = df[
        (df["true_label"] == 1)
        & (df["pred_label"] == 0)
    ].copy()

    false_positives = df[
        (df["true_label"] == 0)
        & (df["pred_label"] == 1)
    ].copy()

    false_negatives.to_csv(fn_path, index=False, encoding="utf-8-sig")
    false_positives.to_csv(fp_path, index=False, encoding="utf-8-sig")

    return result_path, fn_path, fp_path


def generate_report(
    metrics: dict[str, Any],
    df: pd.DataFrame,
    proxy_url: str,
    dataset_name: str,
    split: str,
    max_samples: int,
    result_path: Path,
    fn_path: Path,
    fp_path: Path,
) -> Path:
    report_path = REPORT_DIR / "deepset_prompt_injection_report.md"

    total_samples = len(df)
    error_count = int((df["pred_label"] == -1).sum())

    generated_at = datetime.now().isoformat(timespec="seconds")

    content = f"""# Deepset Prompt Injection Evaluation Report

## 1. Overview

- Generated at: {generated_at}
- Dataset: `{dataset_name}`
- Split: `{split}`
- Requested max samples: {max_samples}
- Total evaluated rows: {total_samples}
- Valid samples: {metrics["valid_samples"]}
- Error samples: {error_count}
- Proxy URL: `{proxy_url}`

This report evaluates the Prompt Injection detection capability of the LLM security proxy using the external Hugging Face dataset `{dataset_name}`.

The dataset is used only for Prompt Injection evaluation. PII detection should continue to be evaluated with a separate Korean PII-focused dataset.

---

## 2. Label Mapping

| Dataset Label | Meaning |
|---|---|
| 0 | Normal / Benign Prompt |
| 1 | Prompt Injection |

---

## 3. Prediction Mapping

| Proxy Response | Predicted Label |
|---|---|
| `action == "BLOCK"` | 1 |
| Other actions | 0 |
| Request or parsing error | -1, excluded from metric calculation |

---

## 4. Metrics

| Metric | Value |
|---|---:|
| Accuracy | {metrics["accuracy"]:.3f} |
| Precision | {metrics["precision"]:.3f} |
| Recall | {metrics["recall"]:.3f} |
| F1-score | {metrics["f1"]:.3f} |

---

## 5. Confusion Matrix

|  | Predicted Normal | Predicted Injection |
|---|---:|---:|
| Actual Normal | {metrics["tn"]} | {metrics["fp"]} |
| Actual Injection | {metrics["fn"]} | {metrics["tp"]} |

---

## 6. Error Analysis Targets

| Type | Meaning | Count |
|---|---|---:|
| False Positive | Normal prompt incorrectly blocked | {metrics["fp"]} |
| False Negative | Injection prompt incorrectly allowed | {metrics["fn"]} |

False Negative cases are especially important for this project because they represent attack prompts that bypassed the proxy.

---

## 7. Generated Files

| File | Description |
|---|---|
| `{result_path}` | Full evaluation result |
| `{fn_path}` | False Negative cases |
| `{fp_path}` | False Positive cases |

---

## 8. Notes

- This external dataset is useful for validating general Prompt Injection detection performance.
- The dataset is mostly English-based, so Korean public-sector scenarios should remain in the project-specific evaluation dataset.
- This result should be presented as an additional external benchmark, not as a replacement for the internal Korean scenario-based testset.
"""

    report_path.write_text(content, encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate proxy Prompt Injection detection using deepset/prompt-injections dataset."
    )

    parser.add_argument(
        "--proxy-url",
        default=DEFAULT_PROXY_URL,
        help=f"Proxy endpoint URL. Default: {DEFAULT_PROXY_URL}",
    )

    parser.add_argument(
        "--dataset-name",
        default=DEFAULT_DATASET_NAME,
        help=f"Hugging Face dataset name. Default: {DEFAULT_DATASET_NAME}",
    )

    parser.add_argument(
        "--split",
        default=DEFAULT_SPLIT,
        help=f"Dataset split. Default: {DEFAULT_SPLIT}",
    )

    parser.add_argument(
        "--max-samples",
        type=int,
        default=DEFAULT_MAX_SAMPLES,
        help=f"Maximum number of samples to evaluate. Default: {DEFAULT_MAX_SAMPLES}",
    )

    parser.add_argument(
        "--model",
        default="mock-llm",
        help="Model name used in proxy request payload. Default: mock-llm",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds. Default: 10",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    ensure_dirs()

    df = evaluate(
        proxy_url=args.proxy_url,
        dataset_name=args.dataset_name,
        split=args.split,
        max_samples=args.max_samples,
        model=args.model,
        timeout=args.timeout,
    )

    metrics = calculate_metrics(df)

    result_path, fn_path, fp_path = save_results(df)

    report_path = generate_report(
        metrics=metrics,
        df=df,
        proxy_url=args.proxy_url,
        dataset_name=args.dataset_name,
        split=args.split,
        max_samples=args.max_samples,
        result_path=result_path,
        fn_path=fn_path,
        fp_path=fp_path,
    )

    print("=== Deepset Prompt Injection Evaluation ===")
    print(f"Dataset       : {args.dataset_name}")
    print(f"Split         : {args.split}")
    print(f"Total rows    : {len(df)}")
    print(f"Valid samples : {metrics['valid_samples']}")
    print(f"Accuracy      : {metrics['accuracy']:.3f}")
    print(f"Precision     : {metrics['precision']:.3f}")
    print(f"Recall        : {metrics['recall']:.3f}")
    print(f"F1-score      : {metrics['f1']:.3f}")
    print()
    print("Confusion Matrix")
    print(f"TN: {metrics['tn']} | FP: {metrics['fp']}")
    print(f"FN: {metrics['fn']} | TP: {metrics['tp']}")
    print()
    print(f"Saved result : {result_path}")
    print(f"Saved FN     : {fn_path}")
    print(f"Saved FP     : {fp_path}")
    print(f"Saved report : {report_path}")


if __name__ == "__main__":
    main()
