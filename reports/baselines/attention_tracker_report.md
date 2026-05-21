# Attention Tracker Baseline Report

## Evaluation Setup

| Item | Value |
|---|---:|
| Dataset source | Capstone GitHub dataset, deepset rows from `datasets/external_splits/` |
| Shared evaluation file | `data/external/attention_tracker/shared_prompt_injection_eval.csv` |
| Shared dataset rows | 100 |
| Attack samples in shared dataset | 44 |
| Benign samples in shared dataset | 56 |
| Successful Attention Tracker rows | 75 |
| Error rows | 25 |
| Focus-score threshold | 0.1200 |

## Metrics

| Metric | Value |
|---|---:|
| Accuracy | 0.7600 |
| Precision | 0.6522 |
| Recall | 0.9375 |
| F1 | 0.7692 |
| AUROC using inverted score | 0.9208 |

## Confusion Matrix

|  | Predicted Benign | Predicted Attack |
|---|---:|---:|
| Actual Benign | 27 | 16 |
| Actual Attack | 2 | 30 |

## Notes

Attention Tracker outputs a focus score where lower scores indicate higher prompt injection likelihood. AUROC is computed with `attack_score = -focus_score`.

Attention Tracker's local reproduction result is computed on the capstone-selected evaluation dataset or subset. It is not identical to the paper's original full evaluation setting.
