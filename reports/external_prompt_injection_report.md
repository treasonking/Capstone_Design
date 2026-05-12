# External Prompt Injection Evaluation Report

## Summary

| Dataset | Size | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepset/prompt-injections | 662 | 1.0000 | 0.0760 | 0.1413 | 0.6329 | 20 | 0 | 399 | 243 |
| protectai/prompt-injection-validation | 3227 | 0.8251 | 0.1796 | 0.2950 | 0.6297 | 250 | 53 | 1782 | 1142 |
| Lakera/gandalf_ignore_instructions | 1000 | N/A | 0.4480 | N/A | 0.4480 | 448 | N/A | N/A | 552 |

## Dataset Sources

| Dataset | Source | License | Role |
|---|---|---|---|
| `deepset/prompt-injections` | [Hugging Face](https://huggingface.co/datasets/deepset/prompt-injections) | cc-by-4.0 | Main external benchmark |
| `protectai/prompt-injection-validation` | [Hugging Face](https://huggingface.co/datasets/protectai/prompt-injection-validation) | Not specified in accessible dataset metadata | Additional large-scale validation |
| `Lakera/gandalf_ignore_instructions` | [Hugging Face](https://huggingface.co/datasets/Lakera/gandalf_ignore_instructions) | Not specified in accessible dataset metadata | Attack-focused recall validation |

## Experiment Roles

| Experiment | Dataset | Purpose |
|---|---|---|
| Experiment A | `deepset/prompt-injections` | Main external Prompt Injection benchmark |
| Experiment B | `protectai/prompt-injection-validation` | Larger additional validation set |
| Experiment C | `Lakera/gandalf_ignore_instructions` | Attack-focused recall validation |
| Experiment D | Internal Korean public-sector scenario dataset | Project-specific regression and public-sector scenario validation |

## Notes

- `deepset/prompt-injections` is used as the main external benchmark dataset because it includes both legitimate and injection prompts.
- `protectai/prompt-injection-validation` is used as an additional larger validation dataset. If the original Hugging Face repo requires authentication in the execution environment, the script falls back to an accessible mirror with the same 3,227-row split structure.
- `Lakera/gandalf_ignore_instructions` is attack-focused, so precision and F1 are marked as `N/A`; its result should be interpreted mainly as recall-oriented validation.
- The previous 24-sample external validation set is retained only as a preliminary validation sample and is not used as the main paper-level performance comparison.
- Dataset contents are loaded from Hugging Face at runtime and are not committed to this repository.

## Paper Wording

기존 외부 검증 데이터셋 24건은 표본 수가 작아 예비 검증 자료로만 활용하였다. 교수 피드백을 반영하여 본 실험에서는 Hugging Face 공개 데이터셋인 `deepset/prompt-injections`, `protectai/prompt-injection-validation`, `Lakera/gandalf_ignore_instructions`를 추가하였다. 이를 통해 Prompt Injection 탐지 성능을 Precision, Recall, F1-score, Accuracy 기준으로 정량 평가하였다.

특히 `deepset/prompt-injections`는 정상 프롬프트와 공격 프롬프트를 모두 포함하므로 본 프로젝트의 메인 외부 성능 비교 데이터셋으로 사용하였다. `protectai/prompt-injection-validation`은 더 큰 규모의 추가 검증셋으로 사용하였고, `Lakera/gandalf_ignore_instructions`는 "ignore previous instructions" 계열 공격 탐지력을 확인하기 위한 공격 특화 Recall 검증셋으로 사용하였다.

기준 논문의 평가 관점을 참고하여 공개 데이터셋 기반 정량 평가를 수행하였다. 데이터셋과 평가 방식이 다르므로 기준 논문과 직접적인 수치 우열 비교는 하지 않는다.