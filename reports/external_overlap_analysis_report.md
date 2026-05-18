# External Rule/Model Overlap Analysis

- Generated at: `2026-05-18T18:31:37`
- Hugging Face split: `all`
- Lightweight threshold: `0.70`
- Model status: `enabled`

## Summary

| Dataset | Rule TP | Model TP | Both TP | Rule Only TP | Model Only Unique TP | Hybrid TP | Hybrid Extra TP |
|---|---:|---:|---:|---:|---:|---:|---:|
| `deepset/prompt-injections` | 20 | 1 | 1 | 19 | 0 | 20 | 0 |
| `protectai/prompt-injection-validation` | 278 | 19 | 19 | 259 | 0 | 278 | 0 |
| `Lakera/gandalf_ignore_instructions` | 440 | 111 | 92 | 348 | 19 | 468 | 28 |

## Interpretation

Hybrid / Full Pipeline 성능이 Rule Only와 유사하게 나타난 주된 이유는 Lightweight Model이 Rule 계층이 놓친 공격 샘플을 거의 추가로 탐지하지 못했기 때문이다.

즉, 현재 외부 영어 데이터셋에서는 Hybrid 성능 향상이 모델 계층이 아니라 대부분 Rule 계층에 의해 결정된다. `Model Only Unique TP`가 0에 가깝다면 `Hybrid TP`는 Rule TP와 거의 같아진다.

`Hybrid Extra TP`는 실제 Hybrid 실행 결과가 Rule Only보다 추가로 맞춘 공격 샘플 수다. 이 값이 `Model Only Unique TP`와 다르면, 현재 Hybrid 내부의 model detector heuristic 또는 fallback reason이 순수 lightweight classifier와 다르게 작동했다는 뜻이다.

샘플 단위의 `expected_injection`, `rule_predicted`, `model_predicted`, `hybrid_predicted` 값은 JSON 결과 파일의 `sample_predictions`에 저장한다.
