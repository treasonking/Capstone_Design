# Multi-Dataset Baseline Comparison

| Dataset | Method | Evaluation scope | Accuracy | Precision | Recall | F1 | AUROC |
|---|---|---|---:|---:|---:|---:|---:|
| deepset | Attention Tracker | Successful rows only | 0.7600 | 0.6522 | 0.9375 | 0.7692 | 0.9208 |
| deepset | Capstone Hybrid Proxy | Same rows as Attention Tracker | 0.6000 | 1.0000 | 0.0625 | 0.1176 | N/A |
| deepset | Capstone Hybrid Proxy | Full selected dataset | 0.5800 | 1.0000 | 0.0455 | 0.0870 | N/A |
| ProtectAI | Attention Tracker | Successful rows only | N/A | N/A | N/A | N/A | N/A |
| ProtectAI | Capstone Hybrid Proxy | Same rows as Attention Tracker | N/A | N/A | N/A | N/A | N/A |
| ProtectAI | Capstone Hybrid Proxy | Full selected dataset | 0.5000 | 0.0000 | 0.0000 | 0.0000 | N/A |
| Lakera | Attention Tracker | Successful rows only | N/A | N/A | N/A | N/A | N/A |
| Lakera | Capstone Hybrid Proxy | Same rows as Attention Tracker | N/A | N/A | N/A | N/A | N/A |
| Lakera | Capstone Hybrid Proxy | Full selected dataset | 0.4800 | 1.0000 | 0.4800 | 0.6486 | N/A |
| Attention Tracker | Paper-reported deepset | Original paper | N/A | N/A | N/A | N/A | 0.98 |

## Interpretation

Attention Tracker local metrics are computed only on successfully evaluated rows. If some rows fail due to local runtime constraints, those rows are excluded from Attention Tracker local metrics and reported separately in the coverage table.

Capstone Hybrid Proxy is evaluated in two ways: full selected dataset and matched subset. The matched subset is used for fair comparison with Attention Tracker, while the full selected dataset shows standalone detector behavior.

Attention Tracker's paper-reported AUROC 0.98 is not a local reproduction result. It is the original paper's Qwen2 1.5B result on deepset.

Attention Tracker AUROC values in local reproduction rows use inverted focus scores: `attack_score = -focus_score`.

## Local Runtime Notes

- ProtectAI Attention Tracker local execution failed in this environment because PyTorch is unavailable (`No module named 'torch'`).
- Lakera Attention Tracker local execution failed in this environment because PyTorch is unavailable (`No module named 'torch'`).
