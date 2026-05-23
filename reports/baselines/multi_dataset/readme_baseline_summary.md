## Multi-Dataset External Baseline Summary

This section summarizes comparison baseline selection and execution pipeline preparation for three external prompt-injection datasets: deepset, ProtectAI, and Lakera.

Capstone Hybrid Proxy has local full evaluation results. PIGuard is the main paper comparison target, while Meta Prompt Guard 2 and ProtectAI detector are selected executable baselines. PIGuard / Meta Prompt Guard 2 / ProtectAI detector remain Pending / Not measured until their models are executed on the shared CSV inputs.

Attention Tracker is excluded from the main local comparison and kept only as related work with paper-reported AUROC reference values.

### Prepared Inputs

| Dataset | Rows | Attack rows | Benign rows | Common-format file |
|---|---:|---:|---:|---|
| deepset | 100 | 44 | 56 | `reports/baselines/multi_dataset/deepset_shared_eval.csv` |
| ProtectAI | 100 | 50 | 50 | `reports/baselines/multi_dataset/protectai_shared_eval.csv` |
| Lakera | 100 | 100 | 0 | `reports/baselines/multi_dataset/lakera_shared_eval.csv` |

### Capstone Hybrid Proxy Local Full Evaluation

| Dataset | Rows | Accuracy | Precision | Recall | F1 | Notes |
|---|---:|---:|---:|---:|---:|---|
| deepset | 100 | 0.5800 | 1.0000 | 0.0455 | 0.0870 | Capstone detector result on the full local selected dataset. |
| ProtectAI | 100 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | Capstone detector result on the full local selected dataset. |
| Lakera | 100 | 0.4800 | 1.0000 | 0.4800 | 0.6486 | Lakera subset is attack-only and should be interpreted as attack recall stress test, not balanced binary classification. Precision is limited because no benign rows exist. |

### Pending / Not Measured Baselines

| Method | Role | Status | Source |
|---|---|---|---|
| PIGuard | Main paper comparison target | Pending / Not measured | `leolee99/PIGuard`; official code `https://github.com/leolee99/PIGuard` |
| Meta Prompt Guard 2 | Execution baseline | Pending / Not measured | `meta-llama/Llama-Prompt-Guard-2-86M` |
| ProtectAI detector | Execution baseline | Pending / Not measured | `protectai/deberta-v3-base-prompt-injection`; fallback `protectai/deberta-v3-small-prompt-injection-v2` |

### Attention Tracker Related-Work Reference

| Dataset | Target model | Result type | AUROC | Note |
|---|---|---|---:|---|
| deepset prompt injection | Qwen2 1.5B | Paper-reported | 0.98 | Related-work reference only; not a local reproduction result. |

### Limitations

- This update prepares comparison baselines and execution pipeline outputs; it does not claim final PIGuard / Prompt Guard 2 / ProtectAI detector performance.
- Lakera is attack-only in the selected local subset, so interpret it as a recall stress test rather than balanced binary classification.
- Capstone Hybrid Proxy results on external English prompt-injection datasets should be interpreted separately from internal public-sector and PII-focused evaluations.
