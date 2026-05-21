# Multi-Dataset Baseline Comparison

| Dataset | Method | Result type | Evaluation scope | Accuracy | Precision | Recall | F1 | AUROC | Notes |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| deepset | Attention Tracker | Local reproduction | Successful rows only | 0.7600 | 0.6522 | 0.9375 | 0.7692 | 0.9208 | Local metrics use successfully evaluated rows only; AUROC uses inverted focus score. |
| deepset | Capstone Hybrid Proxy | Matched local comparison | Same rows as Attention Tracker | 0.6000 | 1.0000 | 0.0625 | 0.1176 | N/A | Same row coverage as Attention Tracker local reproduction. |
| deepset | Capstone Hybrid Proxy | Full capstone evaluation | Full selected dataset | 0.5800 | 1.0000 | 0.0455 | 0.0870 | N/A | Standalone capstone detector result on the full selected dataset. |
| ProtectAI | Attention Tracker | Not executed | Attempted selected dataset | N/A | N/A | N/A | N/A | N/A | Local runtime dependency missing in Codex environment; do not count as performance result. |
| ProtectAI | Capstone Hybrid Proxy | Matched local comparison | Same rows as Attention Tracker | N/A | N/A | N/A | N/A | N/A | No Attention Tracker successful rows; matched comparison is not available. |
| ProtectAI | Capstone Hybrid Proxy | Full capstone evaluation | Full selected dataset | 0.5000 | 0.0000 | 0.0000 | 0.0000 | N/A | Standalone capstone detector result on the full selected dataset. |
| Lakera | Attention Tracker | Not executed | Attempted selected dataset | N/A | N/A | N/A | N/A | N/A | Local runtime dependency missing in Codex environment; do not count as performance result. |
| Lakera | Capstone Hybrid Proxy | Matched local comparison | Same rows as Attention Tracker | N/A | N/A | N/A | N/A | N/A | No Attention Tracker successful rows; matched comparison is not available. |
| Lakera | Capstone Hybrid Proxy | Full capstone evaluation | Full selected dataset | 0.4800 | 1.0000 | 0.4800 | 0.6486 | N/A | Lakera subset is attack-only and should be interpreted as attack recall stress test, not balanced binary classification. Precision is limited because no benign rows exist. |
| deepset | Attention Tracker | Paper-reported | Original paper | N/A | N/A | N/A | N/A | 0.98 | Original paper Qwen2 1.5B result; not a local reproduction result. |

## Interpretation

Attention Tracker local metrics are computed only on successfully evaluated rows. If some rows fail due to local runtime constraints, those rows are excluded from Attention Tracker local metrics and reported separately in the coverage table.

Capstone Hybrid Proxy is evaluated in two ways: full selected dataset and matched subset. The matched subset is used for fair comparison with Attention Tracker, while the full selected dataset shows standalone detector behavior.

Attention Tracker's paper-reported AUROC 0.98 is not a local reproduction result. It is the original paper's Qwen2 1.5B result on deepset.

Attention Tracker AUROC values in local reproduction rows use inverted focus scores: `attack_score = -focus_score`.

Lakera subset is attack-only and should be interpreted as attack recall stress test, not balanced binary classification.

## Local Runtime Notes

- ProtectAI Attention Tracker local metrics were not executed because local runtime dependencies are missing in the Codex environment. This is not a performance result.
- Lakera Attention Tracker local metrics were not executed because local runtime dependencies are missing in the Codex environment. This is not a performance result.
