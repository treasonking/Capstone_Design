# External Rule/Model Overlap Analysis

- Generated at: `2026-05-18T21:36:49`
- Hugging Face split: `datasets/external_splits/eval_external_prompt_injection.jsonl`
- Lightweight threshold: `0.70`
- Model status: `enabled`
- Model version: `internal-only`

## Summary

| Dataset | Model Version | Rule TP | Model TP | Both TP | Rule Only TP | Model Only Unique TP | Hybrid TP | Hybrid Extra TP |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `deepset/prompt-injections` | internal-only | 7 | 0 | 0 | 7 | 0 | 7 | 0 |
| `protectai/prompt-injection-validation` | internal-only | 98 | 8 | 8 | 90 | 0 | 98 | 0 |
| `Lakera/gandalf_ignore_instructions` | internal-only | 129 | 31 | 25 | 104 | 6 | 138 | 9 |

## Interpretation

Hybrid / Full Pipeline 성능이 Rule Only와 유사하게 나타나는 경우, 주된 이유는 Lightweight Model이 Rule 계층이 놓친 공격 샘플을 거의 추가로 탐지하지 못하기 때문이다.

반대로 external-tuned 모델처럼 `Model Only Unique TP`가 증가하면 Hybrid TP도 Rule TP보다 커진다. 따라서 이 표는 Hybrid 개선 여부를 모델 계층의 독립 기여도로 설명하는 핵심 근거다.

`Hybrid Extra TP`는 실제 Hybrid 실행 결과가 Rule Only보다 추가로 맞춘 공격 샘플 수다. 이 값이 `Model Only Unique TP`와 다르면, 현재 Hybrid 내부의 model detector heuristic 또는 fallback reason이 순수 lightweight classifier와 다르게 작동했다는 뜻이다.

샘플 단위의 `expected_injection`, `rule_predicted`, `model_predicted`, `hybrid_predicted` 값은 JSON 결과 파일의 `sample_predictions`에 저장한다.
