# Attention Tracker Related Work

## Placement

Attention Tracker is no longer part of the main quantitative baseline comparison. It should be cited only as related work because it is structurally different from deployable text-guard classifiers and from the Capstone Hybrid Proxy.

## Method Summary

Attention Tracker is a training-free prompt-injection detection method that uses a target LLM's internal attention patterns. Instead of classifying text with an external guard model, it tracks how attention to the trusted instruction changes when untrusted data contains injection content.

This makes it useful as a research comparison, but it is not a direct drop-in baseline for a proxy-style deployment:

| Dimension | Attention Tracker | Capstone Hybrid Proxy / Text-Guard Classifiers |
|---|---|---|
| Required access | Internal attention scores from the target LLM | Text input/output and classifier or proxy signals |
| Deployment fit | Requires model internals or compatible local inference | Can run as an external guard/proxy layer |
| Primary output | Focus/attention score | Binary or policy action such as allow/warn/block |
| Best use in this project | Related work and paper AUROC reference | Main baseline and project performance comparison |

## Paper-Reported AUROC Reference

The Attention Tracker paper reports AUROC on public prompt-injection datasets. These numbers are paper-reported references, not this repository's local reproduction results.

| Dataset | Target model | Attention Tracker AUROC | Reference note |
|---|---|---:|---|
| Open-Prompt-Injection | Qwen2 1.5B | 1.00 | Paper Table 1 reports deterministic Attention Tracker performance. |
| deepset prompt injection | Qwen2 1.5B | 0.98 | Paper Table 1 reports deepset AUROC for Qwen2 1.5B. |
| deepset prompt injection | Phi3 3B | 0.97 | Paper Table 1. |
| deepset prompt injection | Mistral 7B | 0.99 | Paper Table 1. |
| deepset prompt injection | Llama3 8B | 0.99 | Paper Table 1. |
| deepset prompt injection | Gemma2 9B | 0.99 | Paper Table 1. |

## Local Reproduction Note

Earlier repository artifacts include partial local Attention Tracker reproduction attempts under `reports/baselines/` and `reports/baselines/multi_dataset/`. Those artifacts should not be used as the main comparison baseline because row coverage and runtime dependency status differ by dataset.

If mentioned, use language such as:

> Attention Tracker was reviewed as a structurally different research method requiring model attention access. We cite its paper-reported AUROC values for context, while the main baseline plan uses PIGuard, Meta Prompt Guard 2, and ProtectAI detector on shared text-only inputs.

## References

- Attention Tracker paper: https://aclanthology.org/2025.findings-naacl.123.pdf
- Attention Tracker arXiv page: https://arxiv.org/abs/2411.00348
