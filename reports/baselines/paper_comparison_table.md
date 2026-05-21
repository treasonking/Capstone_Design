# Paper Baseline Comparison

## Dataset

| Item | Value |
|---|---:|
| Dataset source | Capstone GitHub dataset (`datasets/external_splits/`, deepset rows) |
| Evaluation file | `data/external/attention_tracker/shared_prompt_injection_eval.csv` |
| Total samples | 100 |
| Attack samples | 44 |
| Benign samples | 56 |
| Evaluation scope | subset-100 |

The full shared dataset contains 100 samples. Attention Tracker succeeded on 75 samples and failed on 25 samples because of local execution environment constraints. Our Capstone Hybrid Proxy was evaluated on the same 75-sample subset that Attention Tracker completed, so the local reproduction rows are aligned.

## Run Coverage

| Method | Result rows | Error count |
|---|---:|---:|
| Attention Tracker | 75 | 25 |
| Our Capstone Hybrid Proxy | 75 | 0 |

## Quantitative Results

| Method | Result Type | Dataset | LLM Internal Access | Black-box API Compatible | PII Detection | Accuracy | Precision | Recall | F1 | AUROC |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|
| Attention Tracker | Local reproduction | Capstone dataset subset | Required | No | No | 0.7600 | 0.6522 | 0.9375 | 0.7692 | 0.9208 |
| Attention Tracker | Paper-reported | deepset/prompt-injections | Required | No | No | N/A | N/A | N/A | N/A | 0.98 |
| Our Capstone Hybrid Proxy | Local reproduction | Same as above | Not required | Yes | Yes | 0.6000 | 1.0000 | 0.0625 | 0.1176 | N/A |

## Interpretation

Attention Tracker is a strong research baseline for prompt injection detection, but it requires access to internal attention scores of the target LLM. This limits direct applicability to black-box LLM API environments.

Our capstone system operates at the proxy layer and does not require access to model internals. It can inspect user input and LLM output, supports PII detection, provides reason codes, and records audit-friendly metadata.

Therefore, Attention Tracker is used as a high-performance research baseline, while the capstone system is evaluated as a deployment-oriented security proxy for public-sector or internal-network environments.

Attention Tracker's local reproduction result is computed on the capstone-selected evaluation dataset or subset. It is not identical to the paper's original full evaluation setting.

The paper-reported AUROC 0.98 refers to Qwen2 1.5B on the deepset prompt injection dataset. Local reproduction metrics are reported separately.

The local Attention Tracker AUROC 0.9208 uses inverted focus scores: `attack_score = -focus_score`.

The Attention Tracker paper-reported AUROC 0.98 is the original paper's reported value, not a locally reproduced score from this run.

Our Capstone Hybrid Proxy's deepset subset F1 0.1176 is an external baseline result showing limitations on English public prompt-injection datasets. It should be interpreted separately from the project's internal public-sector and PII-specialized evaluation results.
