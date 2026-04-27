# Detection Evaluation Report

- Dataset: `datasets/sample_dataset_v2.json`
- Generated at: 2026-04-28T00:32:11
- Dataset size: 129

## Overall

| Scope | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| micro | 0.976 | 0.924 | 0.949 | 121 | 3 | 10 |
| macro | 0.976 | 0.908 | 0.941 | - | - | - |

## Task Metrics

| Task | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| injection | 0.963 | 0.897 | 0.929 | 78 | 3 | 9 |
| pii | 1.000 | 0.977 | 0.989 | 43 | 0 | 1 |

## Label Metrics

| Label | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| INJ_DEBUG_MODE_ATTEMPT | 0.800 | 1.000 | 0.889 | 4 | 1 | 0 |
| INJ_DIRECT_OVERRIDE_ATTEMPT | 1.000 | 0.778 | 0.875 | 7 | 0 | 2 |
| INJ_IGNORE_PREVIOUS_INSTRUCTIONS | 1.000 | 0.875 | 0.933 | 7 | 0 | 1 |
| INJ_MULTI_STEP_EXTRACTION_ATTEMPT | 1.000 | 0.667 | 0.800 | 2 | 0 | 1 |
| INJ_OBFUSCATED_INJECTION_ATTEMPT | 1.000 | 1.000 | 1.000 | 5 | 0 | 0 |
| INJ_POLICY_BYPASS_ATTEMPT | 1.000 | 1.000 | 1.000 | 11 | 0 | 0 |
| INJ_REVEAL_SYSTEM_PROMPT | 0.933 | 1.000 | 0.966 | 14 | 1 | 0 |
| INJ_ROLE_OVERRIDE_ATTEMPT | 1.000 | 0.750 | 0.857 | 3 | 0 | 1 |
| INJ_RULE_DISCLOSURE_ATTEMPT | 1.000 | 0.846 | 0.917 | 11 | 0 | 2 |
| INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT | 0.933 | 0.875 | 0.903 | 14 | 1 | 2 |
| PII_ACCOUNT_DETECTED | 1.000 | 1.000 | 1.000 | 11 | 0 | 0 |
| PII_EMAIL_DETECTED | 1.000 | 1.000 | 1.000 | 12 | 0 | 0 |
| PII_PHONE_DETECTED | 1.000 | 0.923 | 0.960 | 12 | 0 | 1 |
| PII_RRN_DETECTED | 1.000 | 1.000 | 1.000 | 8 | 0 | 0 |

## Category Metrics

| Category | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| inj_boundary | 0.000 | 0.000 | 0.000 | 0 | 2 | 0 |
| inj_debug_policy | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| inj_debug_rule | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| inj_direct_override | 1.000 | 0.667 | 0.800 | 2 | 0 | 1 |
| inj_multi | 1.000 | 1.000 | 1.000 | 3 | 0 | 0 |
| inj_multi_step | 1.000 | 0.400 | 0.571 | 2 | 0 | 3 |
| inj_obfuscated | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| inj_policy_bypass | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| inj_role_rule | 0.667 | 0.500 | 0.571 | 2 | 1 | 2 |
| inj_rule_disclosure | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| inj_system_prompt | 1.000 | 0.800 | 0.889 | 4 | 0 | 1 |
| injection_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| injection_multi | 1.000 | 0.956 | 0.977 | 43 | 0 | 2 |
| injection_negative | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_account | 1.000 | 1.000 | 1.000 | 9 | 0 | 0 |
| pii_account_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_email | 1.000 | 1.000 | 1.000 | 7 | 0 | 0 |
| pii_email_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_multi | 1.000 | 1.000 | 1.000 | 14 | 0 | 0 |
| pii_negative | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_phone | 1.000 | 0.875 | 0.933 | 7 | 0 | 1 |
| pii_phone_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_rrn | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| pii_rrn_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |

## Error Summary

- False positive samples: **2**
- False negative samples: **7**
