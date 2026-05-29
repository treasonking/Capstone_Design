# External Prompt Injection Evaluation Report

## Summary

| Dataset | Size | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| deepset/prompt-injections | 662 | 1.0000 | 0.0760 | 0.1413 | 0.6329 | 20 | 0 | 399 | 243 |
| protectai/prompt-injection-validation | 3227 | 0.8251 | 0.1796 | 0.2950 | 0.6297 | 250 | 53 | 1782 | 1142 |
| Lakera/gandalf_ignore_instructions | 1000 | N/A | 0.4480 | N/A | 0.4480 | 448 | N/A | N/A | 552 |

## Scope Boundary

This report covers Prompt Injection detection on public benchmark datasets only. It is separate from the PAPILLON comparison, which is limited to privacy leakage prevention and privacy-utility trade-off analysis. PAPILLON is not a prompt-injection detector, so it is not included in the deepset, ProtectAI, or Lakera quantitative tables.

## Interpretation

The external benchmark results show a clear performance gap between the internal regression dataset and public prompt injection datasets.

The internal regression dataset mainly verifies whether the project-specific policy rules work correctly in expected public-sector and internal-network scenarios. In contrast, the public datasets include broader English prompt injection patterns, indirect instruction-following attacks, and diverse bypass-style prompts.

Therefore, the low recall and F1-score on external datasets should be interpreted as evidence of limited generalization coverage in the current rule/heuristic-based detector, rather than as a failure of the proxy architecture itself.

The current proxy architecture still provides the following operational controls:

- input-side prompt inspection
- output-side response inspection
- PII masking/blocking
- prompt injection blocking
- reason-code based audit logging
- policy-mode based control

However, the external benchmark indicates that the prompt injection detector should be improved through:

1. expanding English prompt injection patterns,
2. adding multilingual bypass expressions,
3. training or integrating a lightweight classifier,
4. evaluating Rule Only and Hybrid modes separately,
5. maintaining public benchmark evaluation as a regression test.

This external public dataset evaluation was run against the currently active Hybrid Detector configuration. In this environment, the lightweight classifier artifact is loaded, so the reported result reflects the current combined detector behavior rather than a rule-only result.

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

## Relation to Reference Study

본 프로젝트는 Prompt Injection 공격과 방어를 체계적으로 평가한 기준 연구인 *Formalizing and Benchmarking Prompt Injection Attacks and Defenses*의 평가 관점을 참고하였다. 해당 연구는 Prompt Injection 방어 성능을 다양한 task, attack, defense 조합에서 분석하였으며, 탐지 기반 방어의 False Negative Rate와 False Positive Rate를 주요 지표로 사용하였다.

본 프로젝트는 기준 연구의 평가 관점을 참고하되, 실제 공공기관·사내망 환경에서 사용할 수 있는 프록시형 보안 게이트웨이를 구현하는 데 초점을 두었다. 따라서 본 프로젝트의 평가는 Precision, Recall, F1-score, Accuracy를 사용하여 현재 탐지기의 일반화 성능을 확인하는 방식으로 수행하였다.

두 실험은 동일 데이터셋과 동일 방어 방식을 사용하지 않으므로 절대적인 성능 우열 비교는 제한적이다. 대신 본 프로젝트는 기준 연구에서 제시한 Prompt Injection 방어 평가 필요성을 바탕으로, 공개 데이터셋 기반 정량 평가를 추가하고 현재 탐지기의 한계와 개선 방향을 도출하였다.

## Reference Study Source

- Yupei Liu, Yuqi Jia, Runpeng Geng, Jinyuan Jia, and Neil Zhenqiang Gong. "Formalizing and Benchmarking Prompt Injection Attacks and Defenses." USENIX Security 2024. Paper: https://www.usenix.org/conference/usenixsecurity24/presentation/liu-yupei arXiv: https://arxiv.org/abs/2310.12815
- This project references the study's evaluation perspective and metric framing, but it does not directly compare absolute scores because the datasets, defenses, and deployment assumptions differ.

Reference format for the paper body:

- Liu, Y., Jia, Y., Geng, R., Jia, J., & Gong, N. Z. (2024). Formalizing and Benchmarking Prompt Injection Attacks and Defenses. In *Proceedings of the 33rd USENIX Security Symposium* (pp. 1831-1847). USENIX Association.

## Planned Improvements

외부 공개 데이터셋 평가 결과를 바탕으로 다음 개선 작업을 진행할 예정이다.

| Priority | Improvement | Purpose |
|---:|---|---|
| 1 | 영어 기반 Prompt Injection 패턴 확장 | deepset/protectai 데이터셋 Recall 개선 |
| 2 | 한국어·영어 혼합 우회 표현 추가 | 실제 국내 공공기관 사용 환경 반영 |
| 3 | Rule Only와 Hybrid Detector 성능 분리 | 탐지 방식별 기여도 확인 |
| 4 | Lightweight classifier artifact 개선 | rule 기반 탐지 한계 보완 |
| 5 | 외부 데이터셋 회귀 테스트 자동화 | 향후 수정 시 성능 변화 추적 |
| 6 | False Negative 샘플 분석 리포트 추가 | 놓친 공격 유형을 체계적으로 개선 |

## Paper Wording

기존 외부 검증 데이터셋 24건은 표본 수가 작아 예비 검증 자료로만 활용하였다. 교수 피드백을 반영하여 본 실험에서는 Hugging Face 공개 데이터셋인 `deepset/prompt-injections`, `protectai/prompt-injection-validation`, `Lakera/gandalf_ignore_instructions`를 추가하였다. 이를 통해 Prompt Injection 탐지 성능을 Precision, Recall, F1-score, Accuracy 기준으로 정량 평가하였다.

특히 `deepset/prompt-injections`는 정상 프롬프트와 공격 프롬프트를 모두 포함하므로 본 프로젝트의 메인 외부 성능 비교 데이터셋으로 사용하였다. `protectai/prompt-injection-validation`은 더 큰 규모의 추가 검증셋으로 사용하였고, `Lakera/gandalf_ignore_instructions`는 "ignore previous instructions" 계열 공격 탐지력을 확인하기 위한 공격 특화 Recall 검증셋으로 사용하였다.

기준 논문의 평가 관점을 참고하여 공개 데이터셋 기반 정량 평가를 수행하였다. 데이터셋과 평가 방식이 다르므로 기준 논문과 직접적인 수치 우열 비교는 하지 않는다.
