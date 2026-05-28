# Capstone Detector Baseline Report

## Evaluation Setup

| Item | Value |
|---|---:|
| Dataset source | Capstone GitHub dataset, deepset rows from `datasets/external_splits/` |
| Shared evaluation file | `data/external/attention_tracker/shared_prompt_injection_eval.csv` |
| Shared dataset rows | 100 |
| Attack samples in shared dataset | 44 |
| Benign samples in shared dataset | 56 |
| Full capstone rows | 100 |
| Matched capstone rows | 75 |

## Metrics

| Evaluation scope | Accuracy | Precision | Recall | F1 | AUROC |
|---|---:|---:|---:|---:|---:|
| Full 100 rows | 0.5800 | 1.0000 | 0.0455 | 0.0870 | N/A |
| Same successful rows as Attention Tracker | 0.6000 | 1.0000 | 0.0625 | 0.1176 | N/A |

## Comparison Reference

- Kuo-Han Hung, Ching-Yun Ko, Ambrish Rawat, I-Hsin Chung, Winston H. Hsu, and Pin-Yu Chen. "Attention Tracker: Detecting Prompt Injection Attacks in LLMs." Findings of NAACL 2025. Paper: https://aclanthology.org/2025.findings-naacl.123/ arXiv: https://arxiv.org/abs/2411.00348
- This comparison uses Attention Tracker only as a row-alignment reference for the shared evaluation subset. It is based on the paper's described evaluation setting and required attention-score access, and is not a reproduction of the original paper's table.

Reference format for the paper body: Hung, K.-H., Ko, C.-Y., Rawat, A., Chung, I.-H., Hsu, W. H., & Chen, P.-Y. (2025). Attention Tracker: Detecting Prompt Injection Attacks in LLMs. In *Findings of the Association for Computational Linguistics: NAACL 2025*. Association for Computational Linguistics. https://aclanthology.org/2025.findings-naacl.123/

## Prediction Mapping

The capstone detector result is converted to a binary prompt injection prediction from `action` and `reason_codes`.

Rows with injection reason codes such as `INJ_`, `PROMPT_INJECTION`, `JAILBREAK`, `POLICY_BYPASS`, `DIRECT_OVERRIDE`, `SYSTEM_PROMPT`, or `IGNORE_INSTRUCTION` are counted as attack predictions. PII-only reason codes are counted as benign for this prompt injection benchmark.
