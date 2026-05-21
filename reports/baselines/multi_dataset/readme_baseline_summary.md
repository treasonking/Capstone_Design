## Baseline Comparison: Attention Tracker vs. Capstone Hybrid Proxy

This section reports a limited reproduction experiment for a paper baseline, not the main performance claim of this project.

The experiment compares Attention Tracker with the Capstone Hybrid Proxy on three prompt-injection benchmark sources: deepset, ProtectAI, and Lakera. Attention Tracker requires access to internal attention scores, while the Capstone system runs as a deployment-oriented proxy for PII leakage prevention and prompt-injection blocking.

Attention Tracker local metrics are computed only on successfully evaluated rows. Failed rows are reported in the coverage table and are not silently counted as full-dataset performance.

Attention Tracker's paper-reported AUROC 0.98 is listed separately from local reproduction results; it is the original paper's Qwen2 1.5B result on deepset.

Capstone Hybrid Proxy is evaluated both on the full selected dataset and on the matched subset where Attention Tracker produced a local result. Low recall on English public prompt-injection benchmarks should be interpreted as a limitation analysis, separate from internal public-sector and PII-focused evaluations.

deepset has a partial Attention Tracker local reproduction. ProtectAI and Lakera are marked as not executed if the Codex/local runtime cannot provide Attention Tracker dependencies, and those rows are not treated as performance results.

Lakera is attack-only in this selected subset, so it should be read as an attack recall stress test rather than balanced binary classification.

### Coverage

| Dataset | Attention Tracker rows | Attention Tracker errors | Capstone full rows | Capstone matched rows |
|---|---:|---:|---:|---:|
| deepset | 75 | 25 | 100 | 75 |
| ProtectAI | 0 | 100 | 100 | 0 |
| Lakera | 0 | 100 | 100 | 0 |

### Quantitative Summary

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


### Local Runtime Notes

- ProtectAI Attention Tracker local metrics were not executed because local runtime dependencies are missing in the Codex environment. This is not a performance result.
- Lakera Attention Tracker local metrics were not executed because local runtime dependencies are missing in the Codex environment. This is not a performance result.
