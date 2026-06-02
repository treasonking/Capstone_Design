# Baseline and Related Work Comparison

## Scope

This report separates two comparison scopes.

1. Privacy-preserving LLM use and PII leakage mitigation
2. Prompt-injection text guard baselines

PAPILLON is selected as the main paper-level comparison target for privacy-preserving LLM use because it addresses privacy leakage when sensitive user queries are delegated to external or proprietary LLMs.

PIGuard, ProtectAI detector, and Meta Prompt Guard are retained as prompt-injection-related baselines or related work, but they are not the main comparison target for the overall capstone objective.

## Privacy-Preserving LLM Comparison

| Method | Main Objective | Directly executable on PII scenario data | Prompt Injection benchmark target | Notes |
|---|---|---|---|---|
| Capstone Proxy | PII leakage prevention through proxy detection and policy action | Yes | Yes, as a separate module | Proxy-side MASK/BLOCK/WARN |
| PAPILLON | Privacy leakage reduction through local/external LLM delegation | Requires scenario conversion | No | Main paper-level privacy comparison |
| PIGuard | Prompt Injection over-defense mitigation | No for PII | Yes | Related work only |
| ProtectAI detector | Prompt Injection classification | No for PII | Yes | Executable baseline |

PAPILLON is not a prompt-injection binary classifier. It is therefore excluded from the deepset, ProtectAI, and Lakera prompt-injection metric table below.

## Dataset Summary

| Dataset | Rows | Attack | Benign | Notes |
|---|---:|---:|---:|---|
| deepset | 100 | 44 | 56 | selected external prompt-injection subset |
| ProtectAI | 100 | 50 | 50 | selected external detector dataset subset |
| Lakera | 100 | 100 | 0 | attack-only recall stress test |

## Prompt-Injection Text Guard Results

| Dataset | Method | Result type | Accuracy | Precision | Recall | F1 | AUROC | Notes |
|---|---|---|---:|---:|---:|---:|---:|---|
| deepset | Capstone Hybrid Proxy | Local full evaluation | 0.5800 | 1.0000 | 0.0455 | 0.0870 | N/A | proxy-level detector |
| deepset | ProtectAI detector | Local reproduction | 0.7700 | 1.0000 | 0.4773 | 0.6462 | 0.7614 | HF text classifier |
| ProtectAI | Capstone Hybrid Proxy | Local full evaluation | 0.5000 | 0.0000 | 0.0000 | 0.0000 | N/A | proxy-level detector |
| ProtectAI | ProtectAI detector | Local reproduction | 0.5500 | 0.8571 | 0.1200 | 0.2105 | 0.5616 | HF text classifier |
| Lakera | Capstone Hybrid Proxy | Local full evaluation | 0.4800 | 1.0000 | 0.4800 | 0.6486 | N/A | attack-only |
| Lakera | ProtectAI detector | Local reproduction | 0.9900 | 1.0000 | 0.9900 | 0.9950 | N/A | HF text classifier; attack-only |

## Prompt-Injection Related Work and Pending Candidates

| Method | Status | Role | Note |
|---|---|---|---|
| PIGuard | Related work | Prompt Injection over-defense and false-positive analysis | Not the main paper-level comparison target for the capstone proxy's PII leakage objective |
| Meta Prompt Guard 2 | Future executable candidate | Prompt Injection guard model baseline | Local metrics have not been produced yet |
| Attention Tracker | Related work only | Model-internal prompt-injection detection | Excluded from local proxy comparison because it requires internal attention scores |

ProtectAI detector is retained as an executable prompt-injection model baseline for local benchmark comparison. It is not treated as the main paper-level comparison target because it is a detector model rather than a privacy-preserving LLM proxy or privacy delegation framework.

## Comparison Reference

- PAPILLON: Privacy Preservation from Internet-based and Local Language Model Ensembles.
  Paper: https://arxiv.org/abs/2410.17127
  PDF: https://arxiv.org/pdf/2410.17127
  Code: https://github.com/siyan-sylvia-li/PAPILLON
- ProtectAI, `protectai/deberta-v3-base-prompt-injection-v2`, Hugging Face model card. Model: https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2
- Hao Li, Xiaogeng Liu, Ning Zhang, and Chaowei Xiao. "PIGuard: Prompt Injection Guardrail via Mitigating Overdefense for Free." ACL 2025.
  Paper: https://aclanthology.org/2025.acl-long.1468/
  DOI: https://doi.org/10.18653/v1/2025.acl-long.1468
  Code: https://github.com/leolee99/PIGuard
  Note: retained as related work for prompt-injection over-defense, not as the main comparison paper.
- Meta, `meta-llama/Llama-Prompt-Guard-2-22M` and `meta-llama/Llama-Prompt-Guard-2-86M`, Hugging Face model cards, 2025. Models: https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M, https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M
- This comparison is based on the referenced sources' described architecture, supported detection scope, evaluation setting, and deployment assumptions. The table is an interpretive comparison for positioning this project, not a reproduction of an original paper table.

Reference format for the paper body:

- Li, S., Raghuram, V. C., Khattab, O., Hirschberg, J., & Yu, Z. (2024). PAPILLON: Privacy Preservation from Internet-based and Local Language Model Ensembles. arXiv:2410.17127. https://arxiv.org/abs/2410.17127 Official code: https://github.com/siyan-sylvia-li/PAPILLON
- Li, H., Liu, X., Zhang, N., & Xiao, C. (2025). PIGuard: Prompt Injection Guardrail via Mitigating Overdefense for Free. In *Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)* (pp. 30420-30437). Association for Computational Linguistics. https://doi.org/10.18653/v1/2025.acl-long.1468 Official code: https://github.com/leolee99/PIGuard
- ProtectAI. (n.d.). `protectai/deberta-v3-base-prompt-injection-v2` [Hugging Face model card]. Hugging Face. https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2
- Meta. (2025). `Llama-Prompt-Guard-2-22M` and `Llama-Prompt-Guard-2-86M` [Hugging Face model cards]. Hugging Face. https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M

## Interpretation

The Capstone Hybrid Proxy is conservative on external English prompt-injection datasets. It shows low false positives but limited recall, especially on deepset and ProtectAI. ProtectAI detector improves recall on deepset but still shows dataset-dependent behavior.

The Lakera selected subset contains only attack samples. Therefore, its result should be interpreted as an attack-recall stress test rather than balanced binary-classification performance.

PIGuard is retained as related work for prompt-injection over-defense and false-positive analysis, but it is no longer used as the main paper-level comparison target because its primary goal is narrower than the capstone proxy's PII leakage prevention objective. Meta Prompt Guard 2 is still pending as a future executable prompt-injection baseline.

These external prompt-injection datasets are used for generalization analysis, not as the primary project performance benchmark.
