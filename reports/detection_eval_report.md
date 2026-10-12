# Detection Evaluation Report

- Dataset: `datasets/sample_dataset_v2.json`
- Generated at: 2026-07-28T15:39:31
- Dataset size: 152

## Overall

| Scope | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| micro | 0.922 | 1.000 | 0.960 | 166 | 14 | 0 |
| macro | 0.986 | 1.000 | 0.993 | - | - | - |

## Task Metrics

| Task | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| injection | 0.902 | 1.000 | 0.948 | 119 | 13 | 0 |
| pii | 0.979 | 1.000 | 0.989 | 47 | 1 | 0 |

## Label Metrics

| Label | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| INJ_DEBUG_MODE_ATTEMPT | 1.000 | 1.000 | 1.000 | 4 | 0 | 0 |
| INJ_DIRECT_OVERRIDE_ATTEMPT | 0.938 | 1.000 | 0.968 | 15 | 1 | 0 |
| INJ_IGNORE_PREVIOUS_INSTRUCTIONS | 0.938 | 1.000 | 0.968 | 15 | 1 | 0 |
| INJ_MULTI_STEP_EXTRACTION_ATTEMPT | 1.000 | 1.000 | 1.000 | 7 | 0 | 0 |
| INJ_OBFUSCATED_INJECTION_ATTEMPT | 1.000 | 1.000 | 1.000 | 5 | 0 | 0 |
| INJ_POLICY_BYPASS_ATTEMPT | 0.923 | 1.000 | 0.960 | 12 | 1 | 0 |
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
| inj_direct_override | 0.800 | 1.000 | 0.889 | 4 | 1 | 0 |
| inj_multi | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| inj_multi_step | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| inj_obfuscated | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| inj_policy_bypass | 0.667 | 1.000 | 0.800 | 6 | 3 | 0 |
| inj_role_rule | 1.000 | 1.000 | 1.000 | 4 | 0 | 0 |
| inj_rule_disclosure | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| inj_system_prompt | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| injection_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| injection_multi | 0.892 | 1.000 | 0.943 | 74 | 9 | 0 |
| injection_negative | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_account | 1.000 | 1.000 | 1.000 | 9 | 0 | 0 |
| pii_account_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_email | 1.000 | 1.000 | 1.000 | 7 | 0 | 0 |
| pii_email_boundary | 0.000 | 0.000 | 0.000 | 0 | 1 | 0 |
| pii_multi | 1.000 | 1.000 | 1.000 | 14 | 0 | 0 |
| pii_negative | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_phone | 1.000 | 1.000 | 1.000 | 11 | 0 | 0 |
| pii_phone_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_rrn | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| pii_rrn_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |

## Error Summary

- False positive samples: **12**
- False negative samples: **0**
