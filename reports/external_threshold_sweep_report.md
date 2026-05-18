# External Threshold Sweep

- Generated at: `2026-05-18T21:40:32`
- Hugging Face split: `datasets/external_splits/eval_external_prompt_injection.jsonl`
- Thresholds: `0.30, 0.40, 0.50, 0.60, 0.70`
- Model version: `external-tuned`

## Model Status

| Item | Value |
|---|---|
| enabled | True |
| status | enabled |
| note | Lightweight model loaded. |
| vectorizer_path | models\lightweight_external_tuned\vectorizer.joblib |
| classifier_path | models\lightweight_external_tuned\classifier.joblib |

## Results

| Dataset | Model Version | Threshold | Mode | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `deepset/prompt-injections` | external-tuned | 0.30 | Lightweight Model Only | 1.0000 | 0.6076 | 0.7559 | 0.8442 | 48 | 0 | 120 | 31 |
| `deepset/prompt-injections` | external-tuned | 0.30 | Hybrid / Full Pipeline | 1.0000 | 0.6329 | 0.7752 | 0.8543 | 50 | 0 | 120 | 29 |
| `protectai/prompt-injection-validation` | external-tuned | 0.30 | Lightweight Model Only | 0.9946 | 0.8876 | 0.9381 | 0.9494 | 371 | 2 | 549 | 47 |
| `protectai/prompt-injection-validation` | external-tuned | 0.30 | Hybrid / Full Pipeline | 0.9488 | 0.8876 | 0.9172 | 0.9309 | 371 | 20 | 531 | 47 |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.30 | Lightweight Model Only | N/A | 0.9867 | N/A | 0.9867 | 296 | N/A | N/A | 4 |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.30 | Hybrid / Full Pipeline | N/A | 0.9867 | N/A | 0.9867 | 296 | N/A | N/A | 4 |
| `deepset/prompt-injections` | external-tuned | 0.40 | Lightweight Model Only | 1.0000 | 0.6076 | 0.7559 | 0.8442 | 48 | 0 | 120 | 31 |
| `deepset/prompt-injections` | external-tuned | 0.40 | Hybrid / Full Pipeline | 1.0000 | 0.6329 | 0.7752 | 0.8543 | 50 | 0 | 120 | 29 |
| `protectai/prompt-injection-validation` | external-tuned | 0.40 | Lightweight Model Only | 0.9946 | 0.8876 | 0.9381 | 0.9494 | 371 | 2 | 549 | 47 |
| `protectai/prompt-injection-validation` | external-tuned | 0.40 | Hybrid / Full Pipeline | 0.9488 | 0.8876 | 0.9172 | 0.9309 | 371 | 20 | 531 | 47 |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.40 | Lightweight Model Only | N/A | 0.9867 | N/A | 0.9867 | 296 | N/A | N/A | 4 |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.40 | Hybrid / Full Pipeline | N/A | 0.9867 | N/A | 0.9867 | 296 | N/A | N/A | 4 |
| `deepset/prompt-injections` | external-tuned | 0.50 | Lightweight Model Only | 1.0000 | 0.5570 | 0.7154 | 0.8241 | 44 | 0 | 120 | 35 |
| `deepset/prompt-injections` | external-tuned | 0.50 | Hybrid / Full Pipeline | 1.0000 | 0.5823 | 0.7360 | 0.8342 | 46 | 0 | 120 | 33 |
| `protectai/prompt-injection-validation` | external-tuned | 0.50 | Lightweight Model Only | 0.9945 | 0.8660 | 0.9258 | 0.9401 | 362 | 2 | 549 | 56 |
| `protectai/prompt-injection-validation` | external-tuned | 0.50 | Hybrid / Full Pipeline | 0.9478 | 0.8684 | 0.9064 | 0.9226 | 363 | 20 | 531 | 55 |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.50 | Lightweight Model Only | N/A | 0.9867 | N/A | 0.9867 | 296 | N/A | N/A | 4 |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.50 | Hybrid / Full Pipeline | N/A | 0.9867 | N/A | 0.9867 | 296 | N/A | N/A | 4 |
| `deepset/prompt-injections` | external-tuned | 0.60 | Lightweight Model Only | 1.0000 | 0.3797 | 0.5505 | 0.7538 | 30 | 0 | 120 | 49 |
| `deepset/prompt-injections` | external-tuned | 0.60 | Hybrid / Full Pipeline | 1.0000 | 0.4177 | 0.5893 | 0.7688 | 33 | 0 | 120 | 46 |
| `protectai/prompt-injection-validation` | external-tuned | 0.60 | Lightweight Model Only | 1.0000 | 0.8038 | 0.8912 | 0.9154 | 336 | 0 | 551 | 82 |
| `protectai/prompt-injection-validation` | external-tuned | 0.60 | Hybrid / Full Pipeline | 0.9494 | 0.8086 | 0.8734 | 0.8989 | 338 | 18 | 533 | 80 |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.60 | Lightweight Model Only | N/A | 0.9700 | N/A | 0.9700 | 291 | N/A | N/A | 9 |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.60 | Hybrid / Full Pipeline | N/A | 0.9700 | N/A | 0.9700 | 291 | N/A | N/A | 9 |
| `deepset/prompt-injections` | external-tuned | 0.70 | Lightweight Model Only | 1.0000 | 0.1646 | 0.2826 | 0.6683 | 13 | 0 | 120 | 66 |
| `deepset/prompt-injections` | external-tuned | 0.70 | Hybrid / Full Pipeline | 1.0000 | 0.2278 | 0.3711 | 0.6935 | 18 | 0 | 120 | 61 |
| `protectai/prompt-injection-validation` | external-tuned | 0.70 | Lightweight Model Only | 1.0000 | 0.7321 | 0.8453 | 0.8844 | 306 | 0 | 551 | 112 |
| `protectai/prompt-injection-validation` | external-tuned | 0.70 | Hybrid / Full Pipeline | 0.9450 | 0.7392 | 0.8295 | 0.8689 | 309 | 18 | 533 | 109 |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.70 | Lightweight Model Only | N/A | 0.9467 | N/A | 0.9467 | 284 | N/A | N/A | 16 |
| `Lakera/gandalf_ignore_instructions` | external-tuned | 0.70 | Hybrid / Full Pipeline | N/A | 0.9500 | N/A | 0.9500 | 285 | N/A | N/A | 15 |

## Observed Conclusion

- external-tuned 모델에서는 0.70에서도 `protectai`와 `Lakera` Recall이 크게 개선되었지만, `deepset`은 여전히 threshold에 민감하다.
- threshold를 0.30 또는 0.40으로 낮추면 held-out eval split에서 Recall과 F1이 더 좋아지며, 이번 split에서는 FP 증가가 제한적이었다.
- 다만 낮은 threshold는 운영 데이터 분포에서 FP가 달라질 수 있으므로, 추천값은 배포 고정값이 아니라 검증 후보로 해석한다.
- internal-only baseline에서 보였던 Rule Only/Hybrid 유사성은 모델이 rule miss를 거의 추가 탐지하지 못했기 때문이고, external-tuned에서는 Model Unique TP가 증가해 Hybrid 개선이 확인된다.

## Interpretation

- threshold를 낮췄을 때 Lightweight Model Only Recall이 크게 상승하면 기존 threshold가 너무 보수적이었을 가능성이 있다.
- threshold를 낮춰도 Recall이 거의 상승하지 않으면 모델 자체가 영어 공격 표현을 충분히 학습하지 못한 것이다.
- threshold를 낮췄을 때 FP가 급증하면 운영 threshold는 보수적으로 유지하고, 외부 영어 데이터 기반 재학습을 우선 검토한다.
