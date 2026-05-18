# External Model Confidence Analysis

- Generated at: `2026-05-18T18:39:25`
- Hugging Face split: `all`
- Model status: `enabled`

## Confidence by Expected Label

| Dataset | Label | Count | Avg Confidence | >=0.3 | >=0.5 | >=0.7 | Avg Injection Confidence | Inj >=0.3 | Inj >=0.5 | Inj >=0.7 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `deepset/prompt-injections` | injection | 263 | 0.4685 | 1.0000 | 0.3042 | 0.0038 | 0.4662 | 1.0000 | 0.3042 | 0.0038 |
| `deepset/prompt-injections` | benign | 399 | 0.4093 | 1.0000 | 0.0426 | 0.0000 | 0.4007 | 1.0000 | 0.0426 | 0.0000 |
| `protectai/prompt-injection-validation` | injection | 1392 | 0.5590 | 1.0000 | 0.7651 | 0.0136 | 0.5581 | 0.9993 | 0.7651 | 0.0129 |
| `protectai/prompt-injection-validation` | benign | 1835 | 0.4649 | 1.0000 | 0.3259 | 0.0000 | 0.4586 | 0.9989 | 0.3243 | 0.0000 |
| `Lakera/gandalf_ignore_instructions` | injection | 1000 | 0.6185 | 1.0000 | 0.9030 | 0.1110 | 0.6178 | 1.0000 | 0.9030 | 0.1090 |

## Predicted Label Distribution

| Dataset | Predicted Label | Count |
|---|---|---:|
| `deepset/prompt-injections` | INJECTION | 550 |
| `deepset/prompt-injections` | INJECTION_RISK | 1 |
| `deepset/prompt-injections` | PII | 1 |
| `deepset/prompt-injections` | SAFE | 110 |
| `protectai/prompt-injection-validation` | INJECTION | 2901 |
| `protectai/prompt-injection-validation` | INJECTION_RISK | 19 |
| `protectai/prompt-injection-validation` | PII | 6 |
| `protectai/prompt-injection-validation` | SAFE | 301 |
| `Lakera/gandalf_ignore_instructions` | INJECTION | 874 |
| `Lakera/gandalf_ignore_instructions` | INJECTION_RISK | 111 |
| `Lakera/gandalf_ignore_instructions` | SAFE | 15 |

## Observed Conclusion

- 현재 모델은 외부 공격 샘플 상당수를 INJECTION 계열 label로 예측하지만, top confidence가 0.70을 넘는 비율이 낮아 `detected=True`로 인정되는 샘플이 적다.
- benign 샘플도 낮은 threshold에서는 injection confidence가 함께 올라가므로, threshold를 낮추면 Recall과 함께 FP가 증가한다.
- 이 결과는 label mapping 문제보다는 threshold calibration과 외부 영어 데이터 분포에 대한 학습 부족 문제에 가깝다.

## Interpretation

- `Avg Confidence`는 모델이 선택한 top label의 confidence다.
- `Avg Injection Confidence`는 classifier probability 중 injection 계열 label의 confidence다.
- injection 샘플의 top confidence는 높지만 predicted label이 대부분 SAFE/PII이면 threshold 문제가 아니라 label 학습/일반화 문제에 가깝다.
- injection confidence가 전반적으로 낮으면 threshold를 낮춰도 Recall 개선 폭이 제한될 수 있다.
