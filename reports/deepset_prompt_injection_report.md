# Deepset Prompt Injection Evaluation Report

## 1. Overview

- Generated at: 2026-05-12T16:32:44
- Dataset: `deepset/prompt-injections`
- Split: `train`
- Requested max samples: 100
- Total evaluated rows: 100
- Valid samples: 100
- Error samples: 0
- Proxy URL: `http://127.0.0.1:8000/v1/chat/completions`

This report evaluates the Prompt Injection detection capability of the LLM security proxy using the external Hugging Face dataset `deepset/prompt-injections`.

This dataset is used only for Prompt Injection evaluation. PII detection is evaluated separately with Korean PII-focused datasets.

---

## 2. Label Mapping

| Dataset Label | Meaning |
|---|---|
| 0 | Normal / Benign Prompt |
| 1 | Prompt Injection |

---

## 3. Prediction Mapping

| Proxy Response | Predicted Label |
|---|---:|
| `action == "BLOCK"` | 1 |
| Other actions | 0 |
| Request/parsing error | -1 |

Rows with `pred_label = -1` are excluded from metric calculation.

---

## 4. Metrics

| Metric | Value |
|---|---:|
| Accuracy | 0.880 |
| Precision | 1.000 |
| Recall | 0.200 |
| F1-score | 0.333 |

---

## 5. Confusion Matrix

|  | Predicted Normal | Predicted Injection |
|---|---:|---:|
| Actual Normal | 85 | 0 |
| Actual Injection | 12 | 3 |

---

## 6. Error Analysis

| Type | Meaning | Count |
|---|---|---:|
| False Positive | Normal prompt incorrectly blocked | 0 |
| False Negative | Injection prompt incorrectly allowed | 12 |

False Negative cases are the highest-priority review target because they represent prompt injection samples that bypassed the proxy.

---

## 7. Generated Files

| File | Description |
|---|---|
| `evaluation\results\deepset_prompt_injection_results.csv` | Full evaluation result CSV |
| `evaluation\results\deepset_prompt_injection_false_negatives.csv` | False Negative cases |
| `evaluation\results\deepset_prompt_injection_false_positives.csv` | False Positive cases |

---

## 8. Interpretation

This external dataset result should be treated as an additional benchmark for general Prompt Injection detection.

It should not replace:
- internal Korean public-sector scenario tests
- PII detection tests
- manually designed hard-negative tests

The result should be described as external benchmark evidence, not as proof of universal operational detection performance.
