# External Model Confidence Analysis

- Generated at: `2026-05-18T21:37:16`
- Hugging Face split: `datasets\external_splits\eval_external_prompt_injection.jsonl`
- Model status: `enabled`
- Model version: `external-tuned`

## Confidence by Expected Label

| Dataset | Label | Count | Avg Confidence | >=0.3 | >=0.5 | >=0.7 | Avg Injection Confidence | Inj >=0.3 | Inj >=0.5 | Inj >=0.7 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `deepset/prompt-injections` | injection | 79 | 0.6336 | 1.0000 | 0.8987 | 0.2278 | 0.5325 | 0.8987 | 0.5570 | 0.1646 |
| `deepset/prompt-injections` | benign | 120 | 0.7979 | 1.0000 | 1.0000 | 0.9083 | 0.1611 | 0.0333 | 0.0000 | 0.0000 |
| `protectai/prompt-injection-validation` | injection | 418 | 0.8728 | 1.0000 | 0.9689 | 0.7632 | 0.8381 | 0.9593 | 0.8660 | 0.7321 |
| `protectai/prompt-injection-validation` | benign | 551 | 0.8401 | 1.0000 | 1.0000 | 0.9437 | 0.1292 | 0.0200 | 0.0036 | 0.0000 |
| `Lakera/gandalf_ignore_instructions` | injection | 300 | 0.9096 | 1.0000 | 1.0000 | 0.9467 | 0.9074 | 0.9967 | 0.9867 | 0.9467 |

## Predicted Label Distribution

| Dataset | Predicted Label | Count |
|---|---|---:|
| `deepset/prompt-injections` | INJECTION | 35 |
| `deepset/prompt-injections` | INJECTION_RISK | 13 |
| `deepset/prompt-injections` | SAFE | 151 |
| `protectai/prompt-injection-validation` | INJECTION | 67 |
| `protectai/prompt-injection-validation` | INJECTION_RISK | 306 |
| `protectai/prompt-injection-validation` | SAFE | 596 |
| `Lakera/gandalf_ignore_instructions` | INJECTION | 12 |
| `Lakera/gandalf_ignore_instructions` | INJECTION_RISK | 284 |
| `Lakera/gandalf_ignore_instructions` | SAFE | 4 |

## Observed Conclusion

- confidence 분포는 threshold 문제가 큰지, label 학습/일반화 문제가 큰지 구분하기 위한 보조 근거다.
- external-tuned 모델에서는 injection label confidence가 상승했지만, 운영 threshold를 낮출 때는 benign 샘플의 injection confidence와 FP를 함께 확인해야 한다.
- label mapping이 정상이라면 predicted label 분포에서 INJECTION 계열 label이 실제 공격 샘플에 충분히 나타나야 한다.

## Interpretation

- `Avg Confidence`는 모델이 선택한 top label의 confidence다.
- `Avg Injection Confidence`는 classifier probability 중 injection 계열 label의 confidence다.
- injection 샘플의 top confidence는 높지만 predicted label이 대부분 SAFE/PII이면 threshold 문제가 아니라 label 학습/일반화 문제에 가깝다.
- injection confidence가 전반적으로 낮으면 threshold를 낮춰도 Recall 개선 폭이 제한될 수 있다.
