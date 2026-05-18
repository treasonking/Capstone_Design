# External Dataset Rule/Model/Hybrid Comparison

- Generated at: `2026-05-18T18:30:50`
- Hugging Face split: `all`
- Lightweight threshold: `0.70`

본 프로젝트는 범용 Prompt Injection 탐지기가 아니라, 한국어 공공기관·사내망 환경에서 발생할 수 있는 개인정보 유출 및 정책 우회형 Prompt Injection을 우선 방어 대상으로 설계한 LLM 보안 프록시이다.

외부 영어 데이터셋에서 낮은 Recall이 측정된 것은 현재 탐지 정책과 학습 데이터가 한국어 공공기관 시나리오에 집중되어 있기 때문이다. 이 결과는 시스템 실패로 숨기기보다, 범용 환경 확장을 위한 개선 지점으로 해석한다.

## Lightweight Classifier Status

| Item | Value |
|---|---|
| enabled | true |
| status | enabled |
| note | Lightweight model loaded. |
| vectorizer_path | `C:\Users\jho87\Downloads\Capstone_Design\models\lightweight\vectorizer.joblib` |
| classifier_path | `C:\Users\jho87\Downloads\Capstone_Design\models\lightweight\classifier.joblib` |

## Model Version

| Model Version | Training Data | Note |
|---|---|---|
| internal-only | internal Korean public-sector scenario data | No model metadata file found; interpreted as the current internal-oriented artifact. |

## Runtime Versions

| Package | Version |
|---|---|
| datasets | 4.8.5 |
| joblib | 1.5.3 |
| sklearn | 1.8.0 |

## Dataset Loading

| Dataset | Samples | Status | Role | Note |
|---|---:|---|---|---|
| `deepset/prompt-injections` | 662 | loaded | 정상/공격 프롬프트를 모두 포함하는 메인 외부 벤치마크 | - |
| `protectai/prompt-injection-validation` | 3227 | loaded | 3천 건 이상 규모의 추가 검증셋 | - |
| `Lakera/gandalf_ignore_instructions` | 1000 | loaded | 공격 샘플 중심의 ignore-instructions Recall 검증셋 | - |

## Previous Reference

기존 측정값은 비교 기준으로만 둔다. 이번 재평가의 핵심은 아래 `Current Mode Comparison`에서 Rule Only, Lightweight Model Only, Hybrid / Full Pipeline을 분리해 보는 것이다.
기존 입력 문서의 일부 FN 값은 Precision/Recall/Accuracy와 수학적으로 맞지 않아, 저장소의 기존 `reports/external_prompt_injection_report.md` 및 혼동행렬과 일관되는 값으로 표시한다.

| Dataset | Size | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `deepset/prompt-injections` | 662 | 1.0000 | 0.0760 | 0.1413 | 0.6329 | 20 | 0 | 399 | 243 |
| `protectai/prompt-injection-validation` | 3227 | 0.8251 | 0.1796 | 0.2950 | 0.6297 | 250 | 53 | 1782 | 1142 |
| `Lakera/gandalf_ignore_instructions` | 1000 | N/A | 0.4480 | N/A | 0.4480 | 448 | N/A | N/A | 552 |

## Current Mode Comparison

| Dataset | Mode | Size | Precision | Recall | F1 | Accuracy | TP | FP | TN | FN | Avg Latency(ms) | Model Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `deepset/prompt-injections` | Rule Only | 662 | 1.0000 | 0.0760 | 0.1413 | 0.6329 | 20 | 0 | 399 | 243 | 0.605 | disabled |
| `deepset/prompt-injections` | Lightweight Model Only | 662 | 1.0000 | 0.0038 | 0.0076 | 0.6042 | 1 | 0 | 399 | 262 | 0.958 | enabled |
| `deepset/prompt-injections` | Hybrid / Full Pipeline | 662 | 1.0000 | 0.0760 | 0.1413 | 0.6329 | 20 | 0 | 399 | 243 | 1.675 | enabled |
| `protectai/prompt-injection-validation` | Rule Only | 3227 | 0.8399 | 0.1997 | 0.3227 | 0.6384 | 278 | 53 | 1782 | 1114 | 1.049 | disabled |
| `protectai/prompt-injection-validation` | Lightweight Model Only | 3227 | 1.0000 | 0.0136 | 0.0269 | 0.5745 | 19 | 0 | 1835 | 1373 | 1.287 | enabled |
| `protectai/prompt-injection-validation` | Hybrid / Full Pipeline | 3227 | 0.8399 | 0.1997 | 0.3227 | 0.6384 | 278 | 53 | 1782 | 1114 | 3.115 | enabled |
| `Lakera/gandalf_ignore_instructions` | Rule Only | 1000 | N/A | 0.4400 | N/A | 0.4400 | 440 | N/A | N/A | 560 | 0.421 | disabled |
| `Lakera/gandalf_ignore_instructions` | Lightweight Model Only | 1000 | N/A | 0.1110 | N/A | 0.1110 | 111 | N/A | N/A | 889 | 0.867 | enabled |
| `Lakera/gandalf_ignore_instructions` | Hybrid / Full Pipeline | 1000 | N/A | 0.4680 | N/A | 0.4680 | 468 | N/A | N/A | 532 | 1.525 | enabled |

## Hybrid Delta vs Previous

| Dataset | Recall Delta | F1 Delta | Accuracy Delta | TP Delta | FP Delta | FN Delta |
|---|---:|---:|---:|---:|---:|---:|
| `deepset/prompt-injections` | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 | +0.0000 |
| `protectai/prompt-injection-validation` | +0.0201 | +0.0277 | +0.0087 | +28.0000 | +0.0000 | -28.0000 |
| `Lakera/gandalf_ignore_instructions` | +0.0200 | N/A | +0.0200 | +20.0000 | N/A | -20.0000 |

## Why Rule Only and Hybrid are Similar

현재 외부 영어 데이터셋에서는 Hybrid / Full Pipeline 결과가 Rule Only와 거의 동일하게 나타났다. 이는 경량 모델 artifact가 로드되지 않았기 때문이 아니라, 로드된 모델이 Rule 계층이 놓친 영어 공격 샘플을 추가로 거의 탐지하지 못했기 때문이다.

즉, 현재 Hybrid 성능은 대부분 Rule 계층에 의해 결정된다. `Lakera/gandalf_ignore_instructions`에서는 Hybrid가 Rule Only보다 Recall을 0.028 높였으나, `deepset/prompt-injections`와 `protectai/prompt-injection-validation`에서는 모델 계층의 unique TP가 거의 없어 성능 차이가 나타나지 않았다.

이 결과는 경량 분류 계층의 구조적 실패라기보다, 현재 학습 데이터가 한국어 공공기관 시나리오에 집중되어 있어 영어 공개 데이터셋에 대한 일반화가 부족하다는 근거로 해석한다. 정량적인 unique TP 근거는 `reports/external_overlap_analysis_report.md`에서 확인한다.

## Reading Guide

- `Rule Only`는 `backend/app/detection/injection_detector.py`의 규칙·휴리스틱 Prompt Injection 탐지만 사용한다.
- `Lightweight Model Only`는 `models/lightweight/vectorizer.joblib`와 `models/lightweight/classifier.joblib`가 실제로 로드된 경우에만 측정한다.
- `Hybrid / Full Pipeline`은 현재 프로젝트의 다층형 탐지 파이프라인 실행 경로이며, 규칙 탐지와 경량 모델 계층을 함께 사용한다.
- `Lakera/gandalf_ignore_instructions`는 공격 샘플 중심 데이터셋이므로 Precision, F1, FP, TN은 `N/A`로 표시하고 Recall과 Accuracy 중심으로 해석한다.
- `model_status`가 `enabled`가 아니면 Hybrid 결과는 경량 분류 계층이 빠진 fallback 성격이므로 완전한 Hybrid 성능으로 과장하지 않는다.
- sklearn artifact 버전 경고가 발생하면 같은 scikit-learn 버전으로 artifact를 재생성한 뒤 결과를 다시 확인한다.
