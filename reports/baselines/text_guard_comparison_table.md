# Text Guard Baseline Comparison

## Scope

This report compares the Capstone Hybrid Proxy with an executable external text-guard baseline, ProtectAI detector, on three selected external prompt-injection datasets.

PIGuard is selected as the main paper-level comparison target, but local metrics are not included in this revision. Meta Prompt Guard 2 is also retained as a future executable baseline. Attention Tracker is moved to related work because it requires internal LLM attention access.

## Dataset Summary

| Dataset | Rows | Attack | Benign | Notes |
|---|---:|---:|---:|---|
| deepset | 100 | 44 | 56 | selected external prompt-injection subset |
| ProtectAI | 100 | 50 | 50 | selected external detector dataset subset |
| Lakera | 100 | 100 | 0 | attack-only recall stress test |

## Quantitative Results

| Dataset | Method | Result type | Accuracy | Precision | Recall | F1 | AUROC | Notes |
|---|---|---|---:|---:|---:|---:|---:|---|
| deepset | Capstone Hybrid Proxy | Local full evaluation | 0.5800 | 1.0000 | 0.0455 | 0.0870 | N/A | proxy-level detector |
| deepset | ProtectAI detector | Local reproduction | 0.7700 | 1.0000 | 0.4773 | 0.6462 | 0.7614 | HF text classifier |
| deepset | PIGuard | Pending | N/A | N/A | N/A | N/A | N/A | main paper baseline, not measured yet |
| deepset | Meta Prompt Guard 2 | Pending | N/A | N/A | N/A | N/A | N/A | future executable baseline |
| ProtectAI | Capstone Hybrid Proxy | Local full evaluation | 0.5000 | 0.0000 | 0.0000 | 0.0000 | N/A | proxy-level detector |
| ProtectAI | ProtectAI detector | Local reproduction | 0.5500 | 0.8571 | 0.1200 | 0.2105 | 0.5616 | HF text classifier |
| ProtectAI | PIGuard | Pending | N/A | N/A | N/A | N/A | N/A | main paper baseline, not measured yet |
| ProtectAI | Meta Prompt Guard 2 | Pending | N/A | N/A | N/A | N/A | N/A | future executable baseline |
| Lakera | Capstone Hybrid Proxy | Local full evaluation | 0.4800 | 1.0000 | 0.4800 | 0.6486 | N/A | attack-only |
| Lakera | ProtectAI detector | Local reproduction | 0.9900 | 1.0000 | 0.9900 | 0.9950 | N/A | HF text classifier; attack-only |
| Lakera | PIGuard | Pending | N/A | N/A | N/A | N/A | N/A | main paper baseline, not measured yet |
| Lakera | Meta Prompt Guard 2 | Pending | N/A | N/A | N/A | N/A | N/A | future executable baseline |

## Comparison Reference

- ProtectAI, `protectai/deberta-v3-base-prompt-injection-v2`, Hugging Face model card. Model: https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2
- Hao Li, Xiaogeng Liu, Ning Zhang, and Chaowei Xiao. "PIGuard: Prompt Injection Guardrail via Mitigating Overdefense for Free." ACL 2025.  
  Paper: https://aclanthology.org/2025.acl-long.1468/  
  DOI: https://doi.org/10.18653/v1/2025.acl-long.1468  
  Code: https://github.com/leolee99/PIGuard
- Meta, `meta-llama/Llama-Prompt-Guard-2-22M` and `meta-llama/Llama-Prompt-Guard-2-86M`, Hugging Face model cards, 2025. Models: https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M, https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M
- This comparison is based on the referenced sources' described architecture, supported detection scope, evaluation setting, and deployment assumptions. The table is an interpretive comparison for positioning this project, not a reproduction of an original paper table.

Reference format for the paper body:

- Li, H., Liu, X., Zhang, N., & Xiao, C. (2025). PIGuard: Prompt Injection Guardrail via Mitigating Overdefense for Free. In *Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)* (pp. 30420-30437). Association for Computational Linguistics. https://doi.org/10.18653/v1/2025.acl-long.1468 Official code: https://github.com/leolee99/PIGuard
- ProtectAI. (n.d.). `protectai/deberta-v3-base-prompt-injection-v2` [Hugging Face model card]. Hugging Face. https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2
- Meta. (2025). `Llama-Prompt-Guard-2-22M` and `Llama-Prompt-Guard-2-86M` [Hugging Face model cards]. Hugging Face. https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M

## Interpretation

The Capstone Hybrid Proxy is conservative on external English prompt-injection datasets. It shows low false positives but limited recall, especially on deepset and ProtectAI. ProtectAI detector improves recall on deepset but still shows dataset-dependent behavior.

The Lakera selected subset contains only attack samples. Therefore, its result should be interpreted as an attack-recall stress test rather than balanced binary-classification performance.

PIGuard remains the main paper-level text-guard comparison target, but no local PIGuard metrics are reported until its official model/code is executed. Meta Prompt Guard 2 is also still pending.

These external prompt-injection datasets are used for generalization analysis, not as the primary project performance benchmark.
