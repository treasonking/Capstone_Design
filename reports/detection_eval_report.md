# Detection Evaluation Report

- Dataset: `datasets/sample_dataset_v2.json`
- Generated at: 2026-04-28T00:57:17
- Dataset size: 152

## Overall

| Scope | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| micro | 1.000 | 1.000 | 1.000 | 166 | 0 | 0 |
| macro | 1.000 | 1.000 | 1.000 | - | - | - |

## Task Metrics

| Task | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| injection | 1.000 | 1.000 | 1.000 | 119 | 0 | 0 |
| pii | 1.000 | 1.000 | 1.000 | 47 | 0 | 0 |

## Label Metrics

| Label | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| INJ_DEBUG_MODE_ATTEMPT | 1.000 | 1.000 | 1.000 | 4 | 0 | 0 |
| INJ_DIRECT_OVERRIDE_ATTEMPT | 1.000 | 1.000 | 1.000 | 15 | 0 | 0 |
| INJ_IGNORE_PREVIOUS_INSTRUCTIONS | 1.000 | 1.000 | 1.000 | 15 | 0 | 0 |
| INJ_MULTI_STEP_EXTRACTION_ATTEMPT | 1.000 | 1.000 | 1.000 | 7 | 0 | 0 |
| INJ_OBFUSCATED_INJECTION_ATTEMPT | 1.000 | 1.000 | 1.000 | 5 | 0 | 0 |
| INJ_POLICY_BYPASS_ATTEMPT | 1.000 | 1.000 | 1.000 | 12 | 0 | 0 |
| INJ_REVEAL_SYSTEM_PROMPT | 1.000 | 1.000 | 1.000 | 19 | 0 | 0 |
| INJ_ROLE_OVERRIDE_ATTEMPT | 1.000 | 1.000 | 1.000 | 4 | 0 | 0 |
| INJ_RULE_DISCLOSURE_ATTEMPT | 1.000 | 1.000 | 1.000 | 19 | 0 | 0 |
| INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT | 1.000 | 1.000 | 1.000 | 19 | 0 | 0 |
| PII_ACCOUNT_DETECTED | 1.000 | 1.000 | 1.000 | 11 | 0 | 0 |
| PII_EMAIL_DETECTED | 1.000 | 1.000 | 1.000 | 12 | 0 | 0 |
| PII_PHONE_DETECTED | 1.000 | 1.000 | 1.000 | 16 | 0 | 0 |
| PII_RRN_DETECTED | 1.000 | 1.000 | 1.000 | 8 | 0 | 0 |

## Category Metrics

| Category | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| inj_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| inj_debug_policy | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| inj_debug_rule | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| inj_direct_override | 1.000 | 1.000 | 1.000 | 4 | 0 | 0 |
| inj_multi | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| inj_multi_step | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| inj_obfuscated | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| inj_policy_bypass | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| inj_role_rule | 1.000 | 1.000 | 1.000 | 4 | 0 | 0 |
| inj_rule_disclosure | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| inj_system_prompt | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| injection_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| injection_multi | 1.000 | 1.000 | 1.000 | 74 | 0 | 0 |
| injection_negative | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_account | 1.000 | 1.000 | 1.000 | 9 | 0 | 0 |
| pii_account_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_email | 1.000 | 1.000 | 1.000 | 7 | 0 | 0 |
| pii_email_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_multi | 1.000 | 1.000 | 1.000 | 14 | 0 | 0 |
| pii_negative | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_phone | 1.000 | 1.000 | 1.000 | 11 | 0 | 0 |
| pii_phone_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_rrn | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| pii_rrn_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |

## Error Summary

- False positive samples: **0**
- False negative samples: **0**
