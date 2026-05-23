# Text-Guard Baseline Selection And Execution Pipeline

## Scope

Attention Tracker is excluded from the main quantitative baseline table. It remains only as related work and as a paper-reported AUROC reference in `reports/baselines/related_work_attention_tracker.md`.

This document records baseline selection and execution pipeline preparation. It does not claim final performance comparison results for PIGuard / Meta Prompt Guard 2 / ProtectAI detector.

The main external comparison target is now PIGuard. The first executable detector baselines are Meta Prompt Guard 2 and ProtectAI detector:

- PIGuard: `leolee99/PIGuard`, official model/code target for the main guard-model comparison.
- Meta Prompt Guard 2: `meta-llama/Llama-Prompt-Guard-2-86M`.
- ProtectAI detector: `protectai/deberta-v3-base-prompt-injection`, with `protectai/deberta-v3-small-prompt-injection-v2` as a smaller fallback.
- Our Capstone Hybrid Proxy: repository-local hybrid detector output.

## Shared Dataset Inputs

| Dataset key | Dataset source | Shared rows | Attack rows | Benign rows | Common-format file | Note |
|---|---|---:|---:|---:|---|---|
| deepset | `deepset/prompt-injections` | 100 | 44 | 56 | `reports/baselines/multi_dataset/deepset_shared_eval.csv` | Balanced enough for binary metrics. |
| ProtectAI | `protectai/prompt-injection-validation` | 100 | 50 | 50 | `reports/baselines/multi_dataset/protectai_shared_eval.csv` | Balanced subset. |
| Lakera | `Lakera/gandalf_ignore_instructions` | 100 | 100 | 0 | `reports/baselines/multi_dataset/lakera_shared_eval.csv` | Attack-only recall stress test; precision/F1 are limited by missing benign rows. |

## Baseline Pipeline Status

| Method | Role in report | Local result status | Model/source | Execution note |
|---|---|---|---|---|
| PIGuard | Main external guard-model comparison target | Pending / Not measured | `leolee99/PIGuard`; official code repo `https://github.com/leolee99/PIGuard` | Official model/code should be run when Python + Transformers + model access are available. |
| Our Capstone Hybrid Proxy | Project result | Measured as local full evaluation | Repository-local hybrid detector | Results below are from `*_capstone_results_full.csv`. |
| Meta Prompt Guard 2 | First executable text-guard baseline | Pending / Not measured | `meta-llama/Llama-Prompt-Guard-2-86M` | Selected baseline; no measured local result is available yet. |
| ProtectAI detector | First executable text-guard baseline | Pending / Not measured | `protectai/deberta-v3-base-prompt-injection`; fallback `protectai/deberta-v3-small-prompt-injection-v2` | Selected baseline; no measured local result is available yet. |

## Quantitative Results

| Dataset | Method | Result type | Rows | Accuracy | Precision | Recall | F1 | TP | FP | TN | FN | Notes |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| deepset | Our Capstone Hybrid Proxy | Local full evaluation | 100 | 0.5800 | 1.0000 | 0.0455 | 0.0870 | 2 | 0 | 56 | 42 | Conservative detector: no false positives, low external prompt-injection recall. |
| ProtectAI | Our Capstone Hybrid Proxy | Local full evaluation | 100 | 0.5000 | 0.0000 | 0.0000 | 0.0000 | 0 | 0 | 50 | 50 | Current hybrid rules/model do not catch this selected ProtectAI subset. |
| Lakera | Our Capstone Hybrid Proxy | Local full evaluation | 100 | 0.4800 | 1.0000 | 0.4800 | 0.6486 | 48 | 0 | 0 | 52 | Attack-only subset; interpret as recall stress test. |
| deepset | Meta Prompt Guard 2 | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Baseline selected; measured result is not available yet. |
| ProtectAI | Meta Prompt Guard 2 | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Baseline selected; measured result is not available yet. |
| Lakera | Meta Prompt Guard 2 | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Baseline selected; measured result is not available yet. |
| deepset | ProtectAI detector | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Baseline selected; measured result is not available yet. |
| ProtectAI | ProtectAI detector | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Baseline selected; measured result is not available yet. |
| Lakera | ProtectAI detector | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Baseline selected; measured result is not available yet. |
| deepset | PIGuard | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Main comparison target; run official model/code when available. |
| ProtectAI | PIGuard | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Main comparison target; run official model/code when available. |
| Lakera | PIGuard | Pending / Not measured | 0 | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | Main comparison target; run official model/code when available. |

## Reproduction State

Prepared locally:

- Common-format dataset files exist for deepset, ProtectAI, and Lakera under `reports/baselines/multi_dataset/`.
- Our Capstone Hybrid Proxy local full evaluation output exists for all three datasets as `*_capstone_results_full.csv`.

Pending / Not measured:

- Meta Prompt Guard 2 inference has not produced a measured result in this repository yet.
- ProtectAI detector inference has not produced a measured result in this repository yet.
- PIGuard official/model inference has not produced a measured result in this repository yet.

Recommended execution order once Python + dependencies are available:

```powershell
python tools/baselines/prepare_multi_prompt_injection_datasets.py --output-dir reports/baselines/multi_dataset --limit 100
python tools/baselines/run_multi_dataset_capstone_eval.py --input-dir reports/baselines/multi_dataset --output-dir reports/baselines/multi_dataset --detection-mode hybrid
python tools/baselines/run_hf_text_guard_eval.py --model-id meta-llama/Llama-Prompt-Guard-2-86M --input-dir reports/baselines/multi_dataset --output-dir reports/baselines/multi_dataset --method-key prompt_guard_2
python tools/baselines/run_hf_text_guard_eval.py --model-id protectai/deberta-v3-base-prompt-injection --input-dir reports/baselines/multi_dataset --output-dir reports/baselines/multi_dataset --method-key protectai_detector
python tools/baselines/run_hf_text_guard_eval.py --model-id leolee99/PIGuard --input-dir reports/baselines/multi_dataset --output-dir reports/baselines/multi_dataset --method-key piguard --trust-remote-code
```

## Source References

- Meta Prompt Guard 2 model card: https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M
- ProtectAI base detector model card: https://huggingface.co/protectai/deberta-v3-base-prompt-injection
- ProtectAI small v2 detector model card: https://huggingface.co/protectai/deberta-v3-small-prompt-injection-v2
- PIGuard model card: https://huggingface.co/leolee99/PIGuard
- PIGuard official code: https://github.com/leolee99/PIGuard
