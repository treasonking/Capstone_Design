## Baseline Comparison: Attention Tracker vs. Capstone Hybrid Proxy

This section reports a limited reproduction experiment for a paper baseline, not the main performance claim of this project.

The experiment compares Attention Tracker with the Capstone Hybrid Proxy on three prompt-injection benchmark sources: deepset, ProtectAI, and Lakera. Attention Tracker requires access to internal attention scores, while the Capstone system runs as a deployment-oriented proxy for PII leakage prevention and prompt-injection blocking.

Attention Tracker local metrics are computed only on successfully evaluated rows. Failed rows are reported in the coverage table and are not silently counted as full-dataset performance.

Attention Tracker's paper-reported AUROC 0.98 is listed separately from local reproduction results; it is the original paper's Qwen2 1.5B result on deepset.

Capstone Hybrid Proxy is evaluated both on the full selected dataset and on the matched subset where Attention Tracker produced a local result. Low recall on English public prompt-injection benchmarks should be interpreted as a limitation analysis, separate from internal public-sector and PII-focused evaluations.

### Coverage

| Dataset | Attention Tracker rows | Attention Tracker errors | Capstone full rows | Capstone matched rows |
|---|---:|---:|---:|---:|
| deepset | 75 | 25 | 100 | 75 |
| ProtectAI | 0 | 100 | 100 | 0 |
| Lakera | 0 | 100 | 100 | 0 |

### Quantitative Summary

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


### Local Runtime Notes

- ProtectAI Attention Tracker local execution failed in this environment because PyTorch is unavailable (`No module named 'torch'`).
- Lakera Attention Tracker local execution failed in this environment because PyTorch is unavailable (`No module named 'torch'`).
