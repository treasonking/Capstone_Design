# Dataset Bias and Overfitting Check

## 1. Dataset Size
- Total: 5880
- Train: 4080
- Validation: 900
- Test: 900

## 2. Label Distribution
| Label | Count | Ratio |
|---|---:|---:|
| edge_case | 300 | 0.051 |
| injection_risk | 1350 | 0.23 |
| mixed_risk | 240 | 0.041 |
| pii_risk | 1890 | 0.321 |
| safe | 2100 | 0.357 |

## 3. PII Type Distribution
| PII Type | Count |
|---|---:|
| account | 270 |
| address | 510 |
| card | 270 |
| email | 270 |
| ip | 60 |
| name | 60 |
| phone | 780 |
| resident_number | 270 |

## 4. Injection Type Distribution
| Injection Type | Count |
|---|---:|
| data_exfiltration | 510 |
| direct_override | 810 |
| indirect | 270 |
| multi_step | 270 |
| obfuscated | 270 |
| role_play_bypass | 270 |
| system_prompt_leak | 540 |

## 5. Duplication Check
- Exact duplicates: 3500
- Near duplicates: 4820
- Template leakage risk: review-needed

## 6. Split Leakage Check
- Similar templates across train/test: 0
- Same source split issue (train/validation): 0
- Similar templates across validation/test: 0

## 7. Conclusion
- Dataset is balanced enough for baseline hybrid experiments.
