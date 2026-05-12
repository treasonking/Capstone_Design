# External Dataset Performance Summary

## 1. Summary

- Generated at: 2026-05-12T16:32:44
- Dataset: `deepset/prompt-injections`
- Split: `train`
- Requested max samples: 100
- Total rows: 100
- Valid samples: 100
- Error samples: 0

This summary describes the Prompt Injection detection performance of the LLM security proxy on the external Hugging Face dataset `deepset/prompt-injections`.

---

## 2. Main Result

| Metric | Value |
|---|---:|
| Accuracy | 0.880 |
| Precision | 1.000 |
| Recall | 0.200 |
| F1-score | 0.333 |

---

## 3. Confusion Matrix

|  | Predicted Normal | Predicted Injection |
|---|---:|---:|
| Actual Normal | 85 | 0 |
| Actual Injection | 12 | 3 |

---

## 4. Result Interpretation

The external dataset evaluation shows how the proxy performs on Prompt Injection samples that were not manually designed only for this project.

Precision indicates how many blocked prompts were actually injection prompts.

Recall indicates how many actual injection prompts were successfully blocked.

F1-score provides a balanced view of precision and recall.

False Negative cases are more critical than False Positive cases in this project because False Negatives mean that attack prompts bypassed the proxy and reached the upstream LLM.

---

## 5. Recommended Presentation Wording

Use this wording in the report or presentation:

> In addition to the internal Korean public-sector scenario dataset, the project evaluated Prompt Injection detection using the external Hugging Face dataset `deepset/prompt-injections`. This external benchmark provides additional evidence for general Prompt Injection detection performance. The result is reported separately from PII detection because the dataset is focused on Prompt Injection, not Korean personal information leakage.

Avoid this wording:

> The system detects all Prompt Injection attacks.
> The system is 100% accurate in real environments.
> This result proves production-level security.

---

## 6. Limitations

- The dataset is mainly English-based.
- It does not evaluate Korean public-sector PII leakage.
- It does not fully represent indirect prompt injection in document/RAG/tool-use environments.
- It should be used as an external benchmark, not as the only evaluation source.

---

## 7. Next Improvement Targets

1. Review False Negative samples and add missing injection patterns to the rule layer.
2. Review False Positive samples and add hard-negative safe prompts.
3. Compare internal dataset F1 and external dataset F1 separately.
4. Add Korean transformed injection prompts based on the same attack intent.
5. Keep the external benchmark result separate from internal regression test results.
