### External Text-Guard Baseline Evaluation

We evaluated the Capstone Hybrid Proxy on three external prompt-injection datasets: deepset, ProtectAI, and Lakera. We also added ProtectAI's HuggingFace prompt-injection detector as the first executable text-guard baseline.

PIGuard is selected as the main paper-level comparison target because it is an input-text-based prompt guard study, while Attention Tracker is retained only as related work due to its requirement for internal LLM attention access.

Meta Prompt Guard 2 is still an executable baseline candidate, but it has not produced local metrics in this repository yet. PIGuard also remains pending until its official model/code path is executed locally.

These results should be interpreted as external generalization analysis, not as the primary project performance benchmark. The project target remains proxy-level PII leakage prevention, prompt-injection blocking, reason-code generation, and audit-friendly logging for public-sector or internal-network environments.

#### Dataset Coverage

| Dataset | Rows | Attack | Benign | Notes |
|---|---:|---:|---:|---|
| deepset | 100 | 44 | 56 | selected external prompt-injection subset |
| ProtectAI | 100 | 50 | 50 | selected external detector dataset subset |
| Lakera | 100 | 100 | 0 | attack-only recall stress test |

#### Local Metrics Snapshot

| Dataset | Method | Result type | Accuracy | Precision | Recall | F1 | AUROC |
|---|---|---|---:|---:|---:|---:|---:|
| deepset | Capstone Hybrid Proxy | Local full evaluation | 0.5800 | 1.0000 | 0.0455 | 0.0870 | N/A |
| deepset | ProtectAI detector | Local reproduction | 0.7700 | 1.0000 | 0.4773 | 0.6462 | 0.7614 |
| ProtectAI | Capstone Hybrid Proxy | Local full evaluation | 0.5000 | 0.0000 | 0.0000 | 0.0000 | N/A |
| ProtectAI | ProtectAI detector | Local reproduction | 0.5500 | 0.8571 | 0.1200 | 0.2105 | 0.5616 |
| Lakera | Capstone Hybrid Proxy | Local full evaluation | 0.4800 | 1.0000 | 0.4800 | 0.6486 | N/A |
| Lakera | ProtectAI detector | Local reproduction | 0.9900 | 1.0000 | 0.9900 | 0.9950 | N/A |

#### Comparison Reference

- ProtectAI, `protectai/deberta-v3-base-prompt-injection-v2`, Hugging Face model card. Model: https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2
- Li et al., "PIGuard: Prompt Injection Guardrail via Mitigating Overdefense for Free," ACL 2025. Paper: https://aclanthology.org/2025.acl-long.1468/ DOI: https://doi.org/10.18653/v1/2025.acl-long.1468
- Meta, `meta-llama/Llama-Prompt-Guard-2-22M` and `meta-llama/Llama-Prompt-Guard-2-86M`, Hugging Face model cards, 2025. Models: https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M, https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M
- This comparison is based on each source's described architecture, supported detection scope, evaluation setting, and deployment assumptions. It is an interpretive project-positioning comparison, not a reproduction of an original paper table.

Reference format for the paper body: Li, H., Liu, X., Zhang, N., & Xiao, C. (2025). PIGuard: Prompt Injection Guardrail via Mitigating Overdefense for Free. In *Proceedings of ACL 2025* (pp. 30420-30437). Association for Computational Linguistics. https://doi.org/10.18653/v1/2025.acl-long.1468

#### Limitations Observed from External Datasets

The external dataset evaluation shows that the current Capstone Hybrid Proxy is conservative on English prompt-injection corpora. This behavior reduces false positives but significantly lowers recall on general English attack prompts.

The main reasons are:

1. The detector was designed primarily for public-sector/internal-network proxy scenarios.
2. PII leakage prevention and policy-bypass detection are prioritized over broad jailbreak classification.
3. The current rules and lightweight classifier are not yet sufficiently tuned for English prompt-injection corpora.
4. External datasets differ in label distribution and attack style.
5. Lakera selected subset is attack-only, limiting balanced evaluation.

Future work should include English prompt-injection pattern expansion, additional classifier training, and ensemble use with external text-guard models such as ProtectAI detector, Meta Prompt Guard 2, or PIGuard.

#### Pending Baselines

| Method | Status | Note |
|---|---|---|
| PIGuard | Pending | Main paper baseline; local metrics have not been produced yet. |
| Meta Prompt Guard 2 | Pending | Executable candidate; local metrics have not been produced yet. |
| Attention Tracker | Related work only | Excluded from the main local comparison because it requires internal attention scores. |
