# External Dataset Rule/Model/Hybrid Comparison

- Generated at: `2026-05-29T01:57:34`
- Hugging Face split: `datasets\external_splits\eval_external_prompt_injection.jsonl`
- Lightweight threshold: `0.30`

본 프로젝트는 범용 Prompt Injection 탐지기가 아니라, 한국어 공공기관·사내망 환경에서 발생할 수 있는 개인정보 유출 및 정책 우회형 Prompt Injection을 우선 방어 대상으로 설계한 LLM 보안 프록시이다.

외부 영어 데이터셋에서 낮은 Recall이 측정된 것은 현재 탐지 정책과 학습 데이터가 한국어 공공기관 시나리오에 집중되어 있기 때문이다. 이 결과는 시스템 실패로 숨기기보다, 범용 환경 확장을 위한 개선 지점으로 해석한다.

## Lightweight Classifier Status

| Item | Value |
|---|---|
| enabled | true |
| status | enabled |
| note | Lightweight model loaded. |
| vectorizer_path | `models\lightweight_external_tuned\vectorizer.joblib` |
| classifier_path | `models\lightweight_external_tuned\classifier.joblib` |

## Model Version

| Model Version | Training Data | Note |
|---|---|---|
| external-tuned | internal Korean public-sector scenario data + external English prompt injection train partition | External rows use a deterministic train partition. Evaluate external-tuned models on held-out external rows to avoid data leakage. |

## Runtime Versions

| Package | Version |
|---|---|
| datasets | 4.8.5 |
| joblib | 1.5.3 |
| sklearn | 1.7.2 |

## Dataset Loading

| Dataset | Samples | Status | Role | Note |
|---|---:|---|---|---|
| `deepset/prompt-injections` | 199 | loaded | 정상/공격 프롬프트를 모두 포함하는 메인 외부 벤치마크 | Loaded from held-out eval split: datasets\external_splits\eval_external_prompt_injection.jsonl |
| `protectai/prompt-injection-validation` | 969 | loaded | 3천 건 이상 규모의 추가 검증셋 | Loaded from held-out eval split: datasets\external_splits\eval_external_prompt_injection.jsonl |
| `Lakera/gandalf_ignore_instructions` | 300 | loaded | 공격 샘플 중심의 ignore-instructions Recall 검증셋 | Loaded from held-out eval split: datasets\external_splits\eval_external_prompt_injection.jsonl |

## Previous Reference

기존 측정값은 비교 기준으로만 둔다. 이번 재평가의 핵심은 아래 `Current Mode Comparison`에서 Rule Only, Lightweight Model Only, Hybrid / Full Pipeline을 분리해 보는 것이다.
기존 입력 문서의 일부 FN 값은 Precision/Recall/Accuracy와 수학적으로 맞지 않아, 저장소의 기존 `reports/external_prompt_injection_report.md` 및 혼동행렬과 일관되는 값으로 표시한다.

| Dataset | Size | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `deepset/prompt-injections` | 662 | 1.0000 | 0.0760 | 0.1413 | 0.6329 | 20 | 0 | 399 | 243 |
| `protectai/prompt-injection-validation` | 3227 | 0.8251 | 0.1796 | 0.2950 | 0.6297 | 250 | 53 | 1782 | 1142 |
| `Lakera/gandalf_ignore_instructions` | 1000 | N/A | 0.4480 | N/A | 0.4480 | 448 | N/A | N/A | 552 |

## Current Mode Comparison

현재 `Hybrid / Full Pipeline` 행은 prompt-injection benchmark용 calibrated fusion 기준이다. protectai 보정 전 기존 OR 결합 결과와 보정 후 비교는 `reports/protectai_hybrid_fix_report.md`에 별도로 보존한다.

| Dataset | Model Version | Mode | Size | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN | Avg Latency(ms) | Model Status |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `deepset/prompt-injections` | external-tuned | Rule Only | 199 | 1.0000 | 0.0886 | 0.1628 | 0.6382 | 7 | 0 | 120 | 72 | 0.542 | disabled |
| `deepset/prompt-injections` | external-tuned | Lightweight Model Only | 199 | 1.0000 | 0.6076 | 0.7559 | 0.8442 | 48 | 0 | 120 | 31 | 3.082 | enabled |
| `deepset/prompt-injections` | external-tuned | Hybrid / Full Pipeline | 199 | 1.0000 | 0.6076 | 0.7559 | 0.8442 | 48 | 0 | 120 | 31 | 5.754 | enabled |
| `protectai/prompt-injection-validation` | external-tuned | Rule Only | 969 | 0.8448 | 0.2344 | 0.3670 | 0.6512 | 98 | 18 | 533 | 320 | 1.123 | disabled |
| `protectai/prompt-injection-validation` | external-tuned | Lightweight Model Only | 969 | 0.9946 | 0.8876 | 0.9381 | 0.9494 | 371 | 2 | 549 | 47 | 3.731 | enabled |
| `protectai/prompt-injection-validation` | external-tuned | Hybrid / Full Pipeline | 969 | 0.9946 | 0.8876 | 0.9381 | 0.9494 | 371 | 2 | 549 | 47 | 7.539 | enabled |
| `Lakera/gandalf_ignore_instructions` | external-tuned | Rule Only | 300 | N/A | 0.4300 | N/A | 0.4300 | 129 | N/A | N/A | 171 | 0.384 | disabled |
| `Lakera/gandalf_ignore_instructions` | external-tuned | Lightweight Model Only | 300 | N/A | 0.9867 | N/A | 0.9867 | 296 | N/A | N/A | 4 | 3.339 | enabled |
| `Lakera/gandalf_ignore_instructions` | external-tuned | Hybrid / Full Pipeline | 300 | N/A | 0.9867 | N/A | 0.9867 | 296 | N/A | N/A | 4 | 5.563 | enabled |

## Improvement Summary

동일한 held-out eval split에서 internal-only 모델과 external-tuned 모델을 비교한다. 기존 전체 데이터셋 기준 baseline은 위 `Previous Reference`에 보존했다.

| Dataset | Rule Only Recall | Old Hybrid Recall | New Hybrid Recall | Improvement over Rule | Improvement over Old Hybrid |
|---|---:|---:|---:|---:|---:|
| `deepset/prompt-injections` | 0.0886 | 0.0886 | 0.6076 | +0.5190 | +0.5190 |
| `protectai/prompt-injection-validation` | 0.2344 | 0.2344 | 0.8876 | +0.6531 | +0.6531 |
| `Lakera/gandalf_ignore_instructions` | 0.4300 | 0.4600 | 0.9867 | +0.5567 | +0.5267 |

## Model Contribution

| Dataset | Old Model Unique TP | New Model Unique TP | Change |
|---|---:|---:|---:|
| `deepset/prompt-injections` | 0 | 43 | +43.0000 |
| `protectai/prompt-injection-validation` | 0 | 273 | +273.0000 |
| `Lakera/gandalf_ignore_instructions` | 6 | 167 | +161.0000 |

## Threshold

| Dataset | Model Version | Mode | Old Threshold | New Recommended Threshold | Reason |
|---|---|---|---:|---:|---|
| `deepset/prompt-injections` | external-tuned | Hybrid / Full Pipeline | 0.70 | 0.30 | best F1 with precision >= 0.70 preference |
| `protectai/prompt-injection-validation` | external-tuned | Hybrid / Full Pipeline | 0.70 | 0.30 | best F1 with precision >= 0.70 preference |
| `Lakera/gandalf_ignore_instructions` | external-tuned | Hybrid / Full Pipeline | 0.70 | 0.30 | positive-only dataset; recall-oriented recommendation |

## Data Leakage Control

- External datasets were split into train/eval subsets with no train/eval id overlap.
- Normalized text-hash overlap is not zero; treat the custom split metrics as potentially optimistic where exact duplicate text appears across train/eval.
- Random seed: `42`
- Train/eval id overlap: `0`
- Train/eval text-hash overlap: `42`
- Train size: `3421`, eval size: `1468`

| Dataset | Exact Text Overlap | Near Duplicate Count >= 0.95 | Interpretation |
|---|---:|---:|---|
| `deepset/prompt-injections` | 0 | 4 | No exact normalized text overlap, but near duplicates remain; interpret custom split together with official split results. |
| `protectai/prompt-injection-validation` | 41 | N/A | Exact train/eval text overlap is a limitation and may inflate held-out metrics. |
| `Lakera/gandalf_ignore_instructions` | 1 | N/A | Exact train/eval text overlap is a limitation; this dataset is also positive-only, so precision/F1 are not measured. |

## Deepset Result Validation Note

`deepset/prompt-injections`의 external-tuned 결과는 held-out eval split 기준으로 크게 개선되었다. 다만 이 평가는 all split을 프로젝트 내부에서 70/30으로 다시 나눈 custom split 기준이므로, 원본 official split 또는 text-hash leakage 검사를 함께 해석해야 한다. 특히 Precision 1.0000, FP 0이 관찰되므로 label mapping, text overlap, near-duplicate 여부를 추가 확인한다.

관련 검증 보고서: `reports/external_split_leakage_report.md`, `reports/external_label_sanity_check.md`, `reports/deepset_official_split_report.md`, `reports/external_model_confidence_report.md`.

## N/A Interpretation

본 보고서에서 `N/A`는 성능이 0이라는 의미가 아니다. 지표를 계산할 수 없거나 해당 평가 범위에 포함되지 않는 경우를 의미한다.

| N/A 유형 | 원인 | 해당 사례 | 해석 |
|---|---|---|---|
| Positive-only dataset | 데이터셋이 공격 샘플만 포함하여 FP/TN을 정의할 수 없음 | `Lakera/gandalf_ignore_instructions` | Precision/F1 대신 Recall과 Accuracy를 attack-recall stress test로 해석 |
| Model unavailable | 경량 모델 artifact 누락, 의존성 누락, 비활성화, 로딩 실패 | Model Only가 N/A인 경우 | 모델 성능이 0이라는 뜻이 아니라 해당 실행 조건에서 모델 평가가 불가능했다는 의미 |
| Metric not computed | AUROC 등 별도 score 기반 지표를 산출하지 않음 | AUROC N/A | 해당 지표를 측정하지 않았다는 의미 |
| Dataset unavailable | 데이터셋 로딩 실패 또는 샘플 없음 | dataset_status가 unavailable/empty | 평가 대상 데이터가 없어 결과 산출 불가 |
| Scope mismatch | Prompt Injection 데이터셋이므로 PII 성능을 평가하지 않음 | deepset/protectai/Lakera의 PII 결과 | PII 탐지 성능과 별도로 해석 |

특히 `Lakera/gandalf_ignore_instructions`는 공격 중심 데이터셋이므로 정상 샘플 기반의 FP/TN을 계산할 수 없다. 따라서 Precision과 F1은 `N/A`로 표시하고, Recall과 Accuracy를 공격 샘플을 얼마나 탐지했는지 보는 stress test 지표로 해석한다.

## protectai Hybrid Fusion Interpretation

`protectai/prompt-injection-validation` 데이터셋에서 기존 Hybrid OR 결합 방식은 Lightweight Model Only보다 낮은 F1을 보였다. 이는 Rule 계층이 모델이 놓친 공격을 추가로 탐지하지 못하고, 정상 샘플 일부를 prompt injection으로 오탐했기 때문이다.

따라서 protectai 결과는 Hybrid 구조가 항상 단일 모델보다 우수하다는 근거로 사용하지 않는다. 본 프로젝트에서는 해당 결과를 rule severity와 model support threshold가 필요한 사례로 해석한다. 세부 FP 샘플과 reason_code 분석은 `reports/protectai_hybrid_fp_analysis.md`에 기록하고, 보정 전/후 결과는 `reports/protectai_hybrid_fix_report.md`에 기록한다.

## Hybrid Delta vs Previous

아래 표는 기존 전체 데이터셋 기준 수치와의 참고 비교다. 현재 표는 held-out eval split 기준이므로, 같은 split에서의 전/후 비교는 위 `Improvement Summary`를 우선 해석한다.

| Dataset | Recall Delta | F1 Delta | Accuracy Delta | TP Delta | FP Delta | FN Delta |
|---|---:|---:|---:|---:|---:|---:|
| `deepset/prompt-injections` | +0.5316 | +0.6146 | +0.2113 | +28.0000 | +0.0000 | -212.0000 |
| `protectai/prompt-injection-validation` | +0.7080 | +0.6431 | +0.3197 | +121.0000 | -51.0000 | -1095.0000 |
| `Lakera/gandalf_ignore_instructions` | +0.5387 | N/A | +0.5387 | -152.0000 | N/A | -548.0000 |

## Why Rule Only and Hybrid are Similar

internal-only baseline에서는 Hybrid / Full Pipeline 결과가 Rule Only와 거의 동일하게 나타났다. 이는 경량 모델 artifact가 로드되지 않았기 때문이 아니라, 로드된 모델이 Rule 계층이 놓친 영어 공격 샘플을 추가로 거의 탐지하지 못했기 때문이다.

external-tuned 모델에서는 held-out eval split 기준으로 Model Only Unique TP가 증가했다. 따라서 새 Hybrid 성능은 더 이상 Rule 계층만으로 결정되지 않으며, 모델 계층이 rule miss를 실제로 추가 탐지한다.

다만 external-tuned 모델은 영어 공개 데이터셋 train split을 포함한 별도 artifact이므로, 내부 한국어 공공기관 시나리오 성능은 별도로 회귀 검증해야 한다. 정량적인 unique TP 근거는 `reports/external_overlap_analysis_report.md`에서 확인한다.

## Reading Guide

- `Rule Only`는 `backend/app/detection/injection_detector.py`의 규칙·휴리스틱 Prompt Injection 탐지만 사용한다.
- `Lightweight Model Only`는 `models/lightweight/vectorizer.joblib`와 `models/lightweight/classifier.joblib`가 실제로 로드된 경우에만 측정한다.
- `Hybrid / Full Pipeline`은 prompt-injection benchmark 기준에서 PII rule을 제외하고, 모델 탐지 또는 HIGH severity injection rule, 또는 충분한 모델 support가 있는 MEDIUM severity injection rule만 positive로 집계한다.
- `Lakera/gandalf_ignore_instructions`는 공격 샘플 중심 데이터셋이므로 Precision, F1, FP, TN은 `N/A`로 표시하고 Recall과 Accuracy 중심으로 해석한다.
- `model_status`가 `enabled`가 아니면 Hybrid 결과는 경량 분류 계층이 빠진 fallback 성격이므로 완전한 Hybrid 성능으로 과장하지 않는다.
- sklearn artifact 버전 경고가 발생하면 같은 scikit-learn 버전으로 artifact를 재생성한 뒤 결과를 다시 확인한다.
