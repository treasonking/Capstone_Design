# Capstone Detector Baseline Report

## Evaluation Setup

| Item | Value |
|---|---:|
| Dataset source | Capstone GitHub dataset, deepset rows from `datasets/external_splits/` |
| Shared evaluation file | `data/external/attention_tracker/shared_prompt_injection_eval.csv` |
| Shared dataset rows | 100 |
| Attack samples in shared dataset | 44 |
| Benign samples in shared dataset | 56 |
| Full capstone rows | 100 |
| Matched capstone rows | 75 |

## Metrics

| Evaluation scope | Accuracy | Precision | Recall | F1 | AUROC |
|---|---:|---:|---:|---:|---:|
| Full 100 rows | 0.5800 | 1.0000 | 0.0455 | 0.0870 | N/A |
| Same successful rows as Attention Tracker | 0.6000 | 1.0000 | 0.0625 | 0.1176 | N/A |

## Prediction Mapping

The capstone detector result is converted to a binary prompt injection prediction from `action` and `reason_codes`.

Rows with injection reason codes such as `INJ_`, `PROMPT_INJECTION`, `JAILBREAK`, `POLICY_BYPASS`, `DIRECT_OVERRIDE`, `SYSTEM_PROMPT`, or `IGNORE_INSTRUCTION` are counted as attack predictions. PII-only reason codes are counted as benign for this prompt injection benchmark.
