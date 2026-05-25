# Text Guard Baseline Comparison

## Dataset Summary

| Dataset | Rows | Attack | Benign | Notes |
|---|---:|---:|---:|---|
| deepset | 100 | 44 | 56 | balanced or selected subset |
| ProtectAI | 100 | 50 | 50 | selected subset |
| Lakera | 100 | 100 | 0 | attack-only recall stress test |

## Quantitative Results

| Dataset | Method | Result type | Accuracy | Precision | Recall | F1 | AUROC | Notes |
|---|---|---|---:|---:|---:|---:|---:|---|
| deepset | Capstone Hybrid Proxy | Local full evaluation | 0.5800 | 1.0000 | 0.0455 | 0.0870 | N/A | proxy-level detector |
| deepset | ProtectAI detector | Local reproduction | 0.7700 | 1.0000 | 0.4773 | 0.6462 | 0.7614 | HF text classifier `protectai/deberta-v3-base-prompt-injection`. |
| deepset | Meta Prompt Guard 2 | Pending | N/A | N/A | N/A | N/A | N/A | not measured yet |
| deepset | PIGuard | Pending | N/A | N/A | N/A | N/A | N/A | main paper baseline, not measured yet |
| ProtectAI | Capstone Hybrid Proxy | Local full evaluation | 0.5000 | 0.0000 | 0.0000 | 0.0000 | N/A | proxy-level detector |
| ProtectAI | ProtectAI detector | Local reproduction | 0.5500 | 0.8571 | 0.1200 | 0.2105 | 0.5616 | HF text classifier `protectai/deberta-v3-base-prompt-injection`. |
| ProtectAI | Meta Prompt Guard 2 | Pending | N/A | N/A | N/A | N/A | N/A | not measured yet |
| ProtectAI | PIGuard | Pending | N/A | N/A | N/A | N/A | N/A | main paper baseline, not measured yet |
| Lakera | Capstone Hybrid Proxy | Local full evaluation | 0.4800 | 1.0000 | 0.4800 | 0.6486 | N/A | attack-only |
| Lakera | ProtectAI detector | Local reproduction | 0.9900 | 1.0000 | 0.9900 | 0.9950 | N/A | HF text classifier `protectai/deberta-v3-base-prompt-injection`; attack-only recall stress test. |
| Lakera | Meta Prompt Guard 2 | Pending | N/A | N/A | N/A | N/A | N/A | not measured yet |
| Lakera | PIGuard | Pending | N/A | N/A | N/A | N/A | N/A | main paper baseline, not measured yet |

## Interpretation

ProtectAI detector rows marked Local reproduction are executable HuggingFace baseline results produced on the same shared CSV inputs as the Capstone Hybrid Proxy.

PIGuard remains the main paper-level text-guard comparison target, but no local PIGuard metrics are reported until its official model/code is executed. Meta Prompt Guard 2 is also still pending.

Attention Tracker is excluded from the main quantitative table and retained only as related work because it requires internal LLM attention access.

These external prompt-injection datasets are used for generalization analysis, not as the primary project performance benchmark.
