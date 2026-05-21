# Capstone Detector Baseline Report

## Evaluation Setup

| Item | Value |
|---|---:|
| Dataset source | Capstone GitHub dataset, deepset rows from `datasets/external_splits/` |
| Shared evaluation file | `data/external/attention_tracker/shared_prompt_injection_eval.csv` |
| Shared dataset rows | 100 |
| Attack samples in shared dataset | 44 |
| Benign samples in shared dataset | 56 |
| Evaluated capstone rows | 75 |

## Metrics

| Metric | Value |
|---|---:|
| Accuracy | 0.6000 |
| Precision | 1.0000 |
| Recall | 0.0625 |
| F1 | 0.1176 |
| AUROC | N/A |

## Confusion Matrix

|  | Predicted Benign | Predicted Attack |
|---|---:|---:|
| Actual Benign | 43 | 0 |
| Actual Attack | 30 | 2 |

## Prediction Mapping

The capstone detector result is converted to a binary prompt injection prediction from `action` and `reason_codes`.

Rows with injection reason codes such as `INJ_`, `PROMPT_INJECTION`, `JAILBREAK`, `POLICY_BYPASS`, `DIRECT_OVERRIDE`, `SYSTEM_PROMPT`, or `IGNORE_INSTRUCTION` are counted as attack predictions. PII-only reason codes are counted as benign for this prompt injection benchmark.

The capstone detector was evaluated on the same 75-sample subset that Attention Tracker completed, while the full shared dataset contains 100 samples.
