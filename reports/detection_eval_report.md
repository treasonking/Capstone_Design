# Detection Evaluation Report

- Dataset: `datasets/sample_dataset_v2.json`
- Generated at: 2026-04-27T23:21:55
- Dataset size: 117

## Overall

| Scope | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| micro | 0.914 | 0.828 | 0.869 | 96 | 9 | 20 |
| macro | 0.861 | 0.769 | 0.812 | - | - | - |

## Task Metrics

| Task | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| injection | 0.934 | 0.760 | 0.838 | 57 | 4 | 18 |
| pii | 0.886 | 0.951 | 0.918 | 39 | 5 | 2 |

## Label Metrics

| Label | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| INJ_DEBUG_MODE_ATTEMPT | 0.750 | 0.750 | 0.750 | 3 | 1 | 1 |
| INJ_DIRECT_OVERRIDE_ATTEMPT | 1.000 | 0.750 | 0.857 | 6 | 0 | 2 |
| INJ_IGNORE_PREVIOUS_INSTRUCTIONS | 1.000 | 0.857 | 0.923 | 6 | 0 | 1 |
| INJ_MULTI_STEP_EXTRACTION_ATTEMPT | 1.000 | 0.667 | 0.800 | 2 | 0 | 1 |
| INJ_OBFUSCATED_INJECTION_ATTEMPT | 0.000 | 0.000 | 0.000 | 0 | 0 | 2 |
| INJ_POLICY_BYPASS_ATTEMPT | 1.000 | 0.727 | 0.842 | 8 | 0 | 3 |
| INJ_REVEAL_SYSTEM_PROMPT | 0.833 | 1.000 | 0.909 | 10 | 2 | 0 |
| INJ_ROLE_OVERRIDE_ATTEMPT | 1.000 | 0.750 | 0.857 | 3 | 0 | 1 |
| INJ_RULE_DISCLOSURE_ATTEMPT | 1.000 | 0.615 | 0.762 | 8 | 0 | 5 |
| INJ_SYSTEM_PROMPT_EXTRACTION_ATTEMPT | 0.917 | 0.846 | 0.880 | 11 | 1 | 2 |
| PII_ACCOUNT_DETECTED | 0.636 | 0.875 | 0.737 | 7 | 4 | 1 |
| PII_EMAIL_DETECTED | 1.000 | 1.000 | 1.000 | 12 | 0 | 0 |
| PII_PHONE_DETECTED | 0.923 | 0.923 | 0.923 | 12 | 1 | 1 |
| PII_RRN_DETECTED | 1.000 | 1.000 | 1.000 | 8 | 0 | 0 |

## Category Metrics

| Category | Precision | Recall | F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|
| inj_boundary | 0.000 | 0.000 | 0.000 | 0 | 2 | 0 |
| inj_debug_policy | 0.000 | 0.000 | 0.000 | 0 | 0 | 2 |
| inj_debug_rule | 1.000 | 1.000 | 1.000 | 2 | 0 | 0 |
| inj_direct_override | 1.000 | 0.667 | 0.800 | 2 | 0 | 1 |
| inj_multi | 1.000 | 0.667 | 0.800 | 2 | 0 | 1 |
| inj_multi_step | 1.000 | 0.400 | 0.571 | 2 | 0 | 3 |
| inj_obfuscated | 0.750 | 0.600 | 0.667 | 3 | 1 | 2 |
| inj_policy_bypass | 1.000 | 0.833 | 0.909 | 5 | 0 | 1 |
| inj_role_rule | 0.667 | 0.500 | 0.571 | 2 | 1 | 2 |
| inj_rule_disclosure | 1.000 | 0.500 | 0.667 | 3 | 0 | 3 |
| inj_system_prompt | 1.000 | 0.800 | 0.889 | 4 | 0 | 1 |
| injection_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| injection_multi | 1.000 | 0.941 | 0.970 | 32 | 0 | 2 |
| injection_negative | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_account | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| pii_account_boundary | 0.000 | 0.000 | 0.000 | 0 | 2 | 0 |
| pii_boundary | 0.000 | 0.000 | 0.000 | 0 | 1 | 0 |
| pii_email | 1.000 | 1.000 | 1.000 | 7 | 0 | 0 |
| pii_email_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |
| pii_multi | 1.000 | 0.929 | 0.963 | 13 | 0 | 1 |
| pii_negative | 0.000 | 0.000 | 0.000 | 0 | 1 | 0 |
| pii_phone | 1.000 | 0.875 | 0.933 | 7 | 0 | 1 |
| pii_phone_boundary | 0.000 | 0.000 | 0.000 | 0 | 1 | 0 |
| pii_rrn | 1.000 | 1.000 | 1.000 | 6 | 0 | 0 |
| pii_rrn_boundary | 0.000 | 0.000 | 0.000 | 0 | 0 | 0 |

## Error Summary

- False positive samples: **8**
- False negative samples: **16**
