# Text-Guard Baseline Selection And Pipeline Summary

## Current Baseline Direction

The main text-guard comparison is changed from Attention Tracker to PIGuard. Attention Tracker should no longer appear as a main quantitative baseline; it is retained only as related work and as a paper-reported AUROC reference.

This is a baseline selection and execution pipeline preparation update, not a final performance comparison result.

The executable baseline priority is:

1. Meta Prompt Guard 2: `meta-llama/Llama-Prompt-Guard-2-86M`
2. ProtectAI detector: `protectai/deberta-v3-base-prompt-injection`
3. ProtectAI fallback: `protectai/deberta-v3-small-prompt-injection-v2`

PIGuard remains the main external guard-model comparison target when official model/code execution is available.

## Prepared Inputs

The three benchmark sources are already represented in a common CSV format:

| Dataset | Rows | Attack | Benign | File |
|---|---:|---:|---:|---|
| `deepset/prompt-injections` | 100 | 44 | 56 | `reports/baselines/multi_dataset/deepset_shared_eval.csv` |
| `protectai/prompt-injection-validation` | 100 | 50 | 50 | `reports/baselines/multi_dataset/protectai_shared_eval.csv` |
| `Lakera/gandalf_ignore_instructions` | 100 | 100 | 0 | `reports/baselines/multi_dataset/lakera_shared_eval.csv` |

Lakera is attack-only in the selected local subset, so it should be described as a recall stress test rather than a balanced classification benchmark.

## Capstone Local Full Evaluation

Our Capstone Hybrid Proxy is reported as local full evaluation on all three shared datasets:

| Dataset | Accuracy | Precision | Recall | F1 | TP | FP | TN | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| deepset | 0.5800 | 1.0000 | 0.0455 | 0.0870 | 2 | 0 | 56 | 42 |
| ProtectAI | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 50 | 50 |
| Lakera | 0.4800 | 1.0000 | 0.4800 | 0.6486 | 48 | 0 | 0 | 52 |

These results show that the current hybrid detector is conservative on external English prompt-injection corpora: false positives are low, but recall is limited outside the project's internal public-sector and PII-focused scenarios.

## Pending / Not Measured Baselines

Meta Prompt Guard 2, ProtectAI detector, and PIGuard do not yet have measured results in this repository. Do not present these rows as measured local performance until the models are actually executed on the shared CSV inputs.

When the runtime is available, run the text-guard baselines on the same three common-format CSV files and append their metrics to `reports/baselines/text_guard_comparison_table.md`.

## Recommended Claim Wording

Use:

> We prepared deepset, ProtectAI, and Lakera prompt-injection datasets in a common evaluation format and produced Capstone Hybrid Proxy local full evaluation results. This update is a comparison baseline selection and execution pipeline preparation step: PIGuard is the main external guard-model comparison target, while Meta Prompt Guard 2 and ProtectAI detector are the first executable baselines. Attention Tracker is discussed only as related work with paper-reported AUROC values.

Avoid:

> Attention Tracker is the main baseline.

Avoid:

> Prompt Guard 2, ProtectAI detector, or PIGuard outperformed/underperformed on our shared datasets.

That claim is not valid until those models are actually run on the shared CSV inputs.
