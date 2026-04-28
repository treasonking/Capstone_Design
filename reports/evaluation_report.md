# Detection Evaluation Report

- Generated at: 2026-04-28T10:02:02
- Dataset: `evaluation\sample_dataset.json`
- Dataset size: 102

## Summary

| task | precision | recall | f1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| pii | 1.000 | 1.000 | 1.000 | 26 | 0 | 0 |
| injection | 1.000 | 1.000 | 1.000 | 104 | 0 | 0 |

### PII Detection

- Precision: **1.000**
- Recall: **1.000**
- F1: **1.000**
- TP / FP / FN: **26 / 0 / 0**
- False Positives (sample count): **0**
- False Negatives (sample count): **0**

### Prompt Injection Detection

- Precision: **1.000**
- Recall: **1.000**
- F1: **1.000**
- TP / FP / FN: **104 / 0 / 0**
- False Positives (sample count): **0**
- False Negatives (sample count): **0**

## Reason Code Metrics

| reason_code | precision | recall | f1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| INJ_DEBUG_MODE_ATTEMPT | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| INJ_DIRECT_OVERRIDE_ATTEMPT | 1.000 | 1.000 | 1.000 | 15 | 0 | 0 |
| INJ_IGNORE_PREVIOUS_INSTRUCTIONS | 1.000 | 1.000 | 1.000 | 15 | 0 | 0 |
| INJ_MULTI_STEP_EXTRACTION_ATTEMPT | 1.000 | 1.000 | 1.000 | 10 | 0 | 0 |
| INJ_OBFUSCATED_INJECTION_ATTEMPT | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| INJ_POLICY_BYPASS_ATTEMPT | 1.000 | 1.000 | 1.000 | 7 | 0 | 0 |
| INJ_REVEAL_SYSTEM_PROMPT | 1.000 | 1.000 | 1.000 | 17 | 0 | 0 |
| INJ_ROLE_OVERRIDE_ATTEMPT | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| INJ_RULE_DISCLOSURE_ATTEMPT | 1.000 | 1.000 | 1.000 | 15 | 0 | 0 |
| INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT | 1.000 | 1.000 | 1.000 | 17 | 0 | 0 |
| PII_ACCOUNT_DETECTED | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| PII_EMAIL_DETECTED | 1.000 | 1.000 | 1.000 | 4 | 0 | 0 |
| PII_PHONE_DETECTED | 1.000 | 1.000 | 1.000 | 12 | 0 | 0 |
| PII_RRN_DETECTED | 1.000 | 1.000 | 1.000 | 4 | 0 | 0 |

## Focused Risk Areas

### INJ_OBFUSCATED_INJECTION_ATTEMPT

- Precision: **1.000**
- Recall: **1.000**
- F1: **1.000**
- TP / FP / FN: **3 / 0 / 0**

### PII_ACCOUNT_DETECTED

- Precision: **1.000**
- Recall: **1.000**
- F1: **1.000**
- TP / FP / FN: **6 / 0 / 0**

## False Positives

| id | expected | actual | text_excerpt | suspected_cause |
|---|---|---|---|---|
| - | - | - | - | - |

## False Negatives

| id | expected | actual | text_excerpt | suspected_cause |
|---|---|---|---|---|
| - | - | - | - | - |
