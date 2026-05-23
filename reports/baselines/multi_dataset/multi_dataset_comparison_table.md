# Multi-Dataset External Baseline Evaluation

This table records comparison baseline selection and execution pipeline preparation. Capstone Hybrid Proxy has local full evaluation results. PIGuard, Meta Prompt Guard 2, and ProtectAI detector are selected baselines but remain Pending / Not measured until their models are executed on the shared CSV inputs.

Attention Tracker is excluded from the main local comparison and retained only as related work with paper-reported AUROC reference values.

| Dataset | Method | Result type | Evaluation scope | Rows | Accuracy | Precision | Recall | F1 | AUROC | Notes |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---|
| deepset | Capstone Hybrid Proxy | Full | Local full evaluation | 100 | 0.5800 | 1.0000 | 0.0455 | 0.0870 | N/A | Capstone detector result on the full local selected dataset. |
| deepset | Capstone Hybrid Proxy | Matched | Same rows as Attention Tracker successful local attempt | 75 | 0.6000 | 1.0000 | 0.0625 | 0.1176 | N/A | Same row coverage as the historical Attention Tracker successful-row subset. |
| deepset | PIGuard | Not executed | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | Main paper comparison target; selected source `leolee99/PIGuard`; official code `https://github.com/leolee99/PIGuard`. |
| deepset | Meta Prompt Guard 2 | Not executed | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | Execution baseline; selected source `meta-llama/Llama-Prompt-Guard-2-86M`. |
| deepset | ProtectAI detector | Not executed | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | Execution baseline; selected source `protectai/deberta-v3-base-prompt-injection`; fallback `protectai/deberta-v3-small-prompt-injection-v2`. |
| ProtectAI | Capstone Hybrid Proxy | Full | Local full evaluation | 100 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | N/A | Capstone detector result on the full local selected dataset. |
| ProtectAI | Capstone Hybrid Proxy | Matched | Same rows as Attention Tracker successful local attempt | 0 | N/A | N/A | N/A | N/A | N/A | No Attention Tracker successful rows; matched comparison is not available. |
| ProtectAI | PIGuard | Not executed | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | Main paper comparison target; selected source `leolee99/PIGuard`; official code `https://github.com/leolee99/PIGuard`. |
| ProtectAI | Meta Prompt Guard 2 | Not executed | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | Execution baseline; selected source `meta-llama/Llama-Prompt-Guard-2-86M`. |
| ProtectAI | ProtectAI detector | Not executed | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | Execution baseline; selected source `protectai/deberta-v3-base-prompt-injection`; fallback `protectai/deberta-v3-small-prompt-injection-v2`. |
| Lakera | Capstone Hybrid Proxy | Full | Local full evaluation | 100 | 0.4800 | 1.0000 | 0.4800 | 0.6486 | N/A | Lakera subset is attack-only and should be interpreted as attack recall stress test, not balanced binary classification. Precision is limited because no benign rows exist. |
| Lakera | Capstone Hybrid Proxy | Matched | Same rows as Attention Tracker successful local attempt | 0 | N/A | N/A | N/A | N/A | N/A | No Attention Tracker successful rows; matched comparison is not available. |
| Lakera | PIGuard | Not executed | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | Main paper comparison target; selected source `leolee99/PIGuard`; official code `https://github.com/leolee99/PIGuard`. |
| Lakera | Meta Prompt Guard 2 | Not executed | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | Execution baseline; selected source `meta-llama/Llama-Prompt-Guard-2-86M`. |
| Lakera | ProtectAI detector | Not executed | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | Execution baseline; selected source `protectai/deberta-v3-base-prompt-injection`; fallback `protectai/deberta-v3-small-prompt-injection-v2`. |
| deepset | Attention Tracker | Paper-reported | Related work only | N/A | N/A | N/A | N/A | N/A | 0.98 | Original paper Qwen2 1.5B result; not a local reproduction result and not part of the main local comparison. |

## Interpretation

Capstone Hybrid Proxy is reported as local full evaluation on the three shared datasets. Matched rows are included only to preserve compatibility with the historical Attention Tracker reproduction artifacts.

PIGuard is the main paper comparison target. Meta Prompt Guard 2 and ProtectAI detector are executable baselines. They are Pending / Not measured until their HuggingFace models are run on the shared CSV inputs.

Attention Tracker is discussed only as related work here. Its paper-reported deepset AUROC 0.98 is not a local reproduction result.

Lakera subset is attack-only and should be interpreted as attack recall stress test, not balanced binary classification.
