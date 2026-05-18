# Rule Only vs Hybrid Baseline Comparison

본 프로젝트는 범용 Prompt Injection 탐지기가 아니라, 한국어 공공기관·사내망 환경에서 발생할 수 있는 개인정보 유출 및 정책 우회형 Prompt Injection을 우선 방어 대상으로 설계한 LLM 보안 프록시이다.

외부 영어 데이터셋에서 낮은 Recall이 측정된 것은 현재 탐지 정책과 학습 데이터가 한국어 공공기관 시나리오에 집중되어 있기 때문이다. 이 결과는 시스템 실패로 숨기기보다, 범용 환경 확장을 위한 개선 지점으로 해석한다.

## Lightweight Classifier Status

| Item | Value |
|---|---|
| model_status | enabled |
| enabled | true |
| vectorizer_path | `C:\Users\jho87\Downloads\Capstone_Design\models\lightweight\vectorizer.joblib` |
| classifier_path | `C:\Users\jho87\Downloads\Capstone_Design\models\lightweight\classifier.joblib` |
| note | Lightweight model loaded. |

Lightweight classifier artifact가 존재하지 않는 경우 시스템은 실행 중단 대신 rule-based fallback으로 동작한다. 이는 데모 안정성을 위한 설계이나, Hybrid 성능 평가에서는 `model_status`를 `artifact_missing`으로 분리 표시한다. 따라서 fallback 상태의 결과를 완전한 Hybrid 성능으로 해석하지 않는다.

## Datasets

| Dataset | Samples | Status | Note |
|---|---:|---|---|
| internal | 110 | loaded | - |
| deepset | 0 | skipped | Skipped by --max-deepset-samples 0. |

## Results

| Dataset | Mode | Precision | Recall | F1 | TP | FP | FN | Avg Latency(ms) | Model Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| internal | Rule Only | 1.000 | 1.000 | 1.000 | 79 | 0 | 0 | 1.154 | disabled |
| internal | Model Only | 1.000 | 0.127 | 0.225 | 10 | 0 | 69 | 2.994 | enabled |
| internal | Hybrid | 1.000 | 1.000 | 1.000 | 79 | 0 | 0 | 3.724 | enabled |
| deepset | Rule Only | N/A | N/A | N/A | N/A | N/A | N/A | N/A | skipped |
| deepset | Model Only | N/A | N/A | N/A | N/A | N/A | N/A | N/A | skipped |
| deepset | Hybrid | N/A | N/A | N/A | N/A | N/A | N/A | N/A | skipped |

## Reading Guide

- `Rule Only`는 regex/rule 기반 Prompt Injection 탐지만 사용한다.
- `Model Only`는 `models/lightweight/vectorizer.joblib`, `models/lightweight/classifier.joblib`가 모두 로드된 경우에만 측정한다. artifact가 없으면 `N/A`로 표시한다.
- `Hybrid(fallback)`은 경량 분류 artifact가 없거나 사용할 수 없어 rule 기반 fallback 경로로 평가된 상태이다. 이 값은 완전한 Hybrid 성능으로 과장하지 않는다.
- 외부 영어 데이터셋 결과는 한국어 공공기관·사내망 특화 정책의 일반화 한계를 확인하기 위한 보조 근거로 사용한다.
