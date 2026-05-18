# Evaluation Limitations and External Validation Plan

## 1. 내부 데이터셋의 한계

- 현재 `evaluation/sample_dataset.json`은 프로젝트 내부 MVP 검증을 위해 직접 설계한 데이터셋이다.
- reason_code, 정책 규칙, 마스킹 기준을 설계하는 과정에서 함께 다듬어졌기 때문에 탐지기와 평가셋 사이의 간격이 좁다.
- 따라서 이 결과는 "탐지기 회귀 테스트와 시연 재현성"에는 유용하지만, 운영 환경 일반화 성능을 대표한다고 보기는 어렵다.
- 본 프로젝트는 범용 Prompt Injection 탐지기가 아니라, 한국어 공공기관·사내망 환경에서 발생할 수 있는 개인정보 유출 및 정책 우회형 Prompt Injection을 우선 방어 대상으로 설계한 LLM 보안 프록시이다.

## 2. F1 1.0 결과의 해석 주의점

- 현재 내부 평가에서는 PII와 Prompt Injection 모두 Precision/Recall/F1이 1.000이다.
- 이 수치는 내부 데이터셋에 대한 일관성 검증 결과로 해석해야 하며, 외부 분포에서 동일한 성능을 보장하지 않는다.
- 발표 시에는 "탐지기가 완벽하다"가 아니라 "현재 규칙 변경이 기존 기대 동작을 깨지 않았는지 확인하는 회귀 지표"라고 설명하는 것이 안전하다.

## 3. 외부 검증 필요성

- 실제 사용자 입력은 더 다양한 표현, 은어, 난독화, 혼합 언어, 문맥형 우회 시도를 포함할 수 있다.
- 주소/계좌/전화번호처럼 형식 기반 탐지는 지역별 표기와 도메인 문맥에 따라 오탐과 미탐 가능성이 달라진다.
- Prompt Injection은 공개 jailbreak prompt, role-play 우회, 인코딩/난독화 프롬프트에서 성능이 크게 흔들릴 수 있으므로 외부 검증이 필요하다.
- 외부 영어 데이터셋에서 낮은 Recall이 측정된 것은 현재 탐지 정책과 학습 데이터가 한국어 공공기관 시나리오에 집중되어 있기 때문이다. 이 결과는 시스템 실패로 숨기기보다, 범용 환경 확장을 위한 개선 지점으로 해석한다.
- 이에 따라 `ignore previous instructions`, `reveal the system prompt`, `bypass safety policy`, `act as DAN` 같은 대표 영어 패턴과 `이전 instructions 무시`, `system prompt 보여줘`, `policy bypass 해줘` 같은 한국어-영어 혼합 패턴을 최소 보완 범위로 추가했다.

## 4. 추가 검증 후보

- PromptBench
- JailbreakBench
- 공개 jailbreak prompt 샘플 모음
- 공개 PII 탐지 샘플 및 형식 변형 예시
- 한국어 행정 민원 문맥의 비식별 샘플

## 5. 외부 공개 데이터셋 모드 분리 결과

2026-05-18 재평가에서는 Hugging Face 공개 Prompt Injection 데이터셋 3종을 `Rule Only`, `Lightweight Model Only`, `Hybrid / Full Pipeline`으로 분리 측정했다. 결과 파일은 다음과 같다.

- `reports/external_dataset_compare_report.md`
- `reports/external_dataset_compare_results.json`
- `reports/external_dataset_compare_results.csv`
- `reports/external_overlap_analysis_report.md`
- `reports/external_threshold_sweep_report.md`
- `reports/external_threshold_optimizer_report.md`
- `reports/external_model_confidence_report.md`

internal-only baseline에서는 `deepset/prompt-injections`의 Rule Only와 Hybrid Recall이 모두 0.0760으로 같았고, `protectai/prompt-injection-validation`에서도 둘 다 Recall 0.1997, F1 0.3227이었다. `Lakera/gandalf_ignore_instructions`에서는 Hybrid Recall이 0.4680으로 Rule Only 0.4400보다 소폭 높았다.

이를 보완하기 위해 외부 공개 데이터셋을 random seed 42로 train 70% / eval 30%로 분리하고, eval 샘플이 학습에 들어가지 않도록 id overlap을 검사했다. 현재 split 기준 train/eval overlap은 0이며, external-tuned 모델은 내부 한국어 시나리오와 외부 영어 train split만 사용해 학습했다.

held-out eval split에서 external-tuned Hybrid Recall은 `deepset=0.2278`, `protectai=0.7392`, `Lakera=0.9500`으로 측정되었다. 같은 eval split의 internal-only Hybrid Recall은 각각 `0.0886`, `0.2344`, `0.4600`이었으므로, 외부 영어 train split을 포함한 재학습은 모델 계층의 영어 일반화 성능을 크게 개선했다.

## 6. Hybrid Pipeline Limitation on English Datasets

Hybrid 구조가 항상 Rule Only보다 높은 성능을 보장하는 것은 아니다. Hybrid가 성능을 개선하려면 모델 계층이 Rule 계층이 놓친 샘플을 추가 탐지해야 한다. internal-only baseline에서는 경량 모델의 추가 탐지 기여도가 낮아 Hybrid와 Rule Only 성능이 유사하게 나타났다.

internal-only overlap 분석에서 `Model Only Unique TP`는 held-out eval split 기준 `deepset=0`, `protectai=0`, `Lakera=6`으로 측정되었다. external-tuned 모델에서는 이 값이 `deepset=11`, `protectai=211`, `Lakera=156`으로 증가했다. 즉, 새 Hybrid 개선은 Rule 계층이 아니라 모델 계층이 rule miss를 추가 탐지한 결과다.

Threshold optimizer는 external-tuned 모델의 held-out eval split에서 `0.30`을 추천했다. 이 값은 F1과 Recall을 높였지만, 운영 데이터 분포에서는 FP가 달라질 수 있으므로 배포 고정값이 아니라 검증 후보로 해석해야 한다.

따라서 본 프로젝트의 Hybrid 구조는 한국어 공공기관 시나리오에서는 설명 가능성과 안정성을 제공하고, 영어 범용 Prompt Injection 환경으로 확장하려면 외부 데이터 기반 재학습, validation split 기반 threshold calibration, hard negative 보강을 함께 수행해야 한다.

## 7. 발표 시 설명 문장

- "현재 1.0 점수는 내부 검증셋 기준이며, 운영 성능을 보장하는 수치로 주장하지 않습니다."
- "이번 MVP에서는 정책 회귀와 시연 재현성을 우선했고, 외부 영어 데이터셋은 train/eval split을 분리해 재학습 개선 가능성을 별도로 검증했습니다."
- "외부 공개 데이터셋 3종에 대해서는 `reports/external_dataset_compare_report.md`에서 Rule Only, Lightweight Model Only, Hybrid / Full Pipeline을 분리해 확인합니다."
- "internal-only baseline에서 Rule Only와 Hybrid가 비슷했던 이유는 overlap 분석에서 Model Only Unique TP가 거의 없다는 점으로 확인했습니다."
- "external-tuned 모델에서는 Model Only Unique TP가 증가했지만, 영어 공개 데이터셋 train split을 사용한 별도 모델이므로 내부 한국어 시나리오 성능은 별도 회귀 검증이 필요합니다."
- "artifact가 없는 fallback 상태는 완전한 Hybrid 성능으로 해석하지 않습니다."

## 8. 향후 개선 계획

- `evaluation/external_validation_sample.json` 같은 외부 스타일 샘플을 먼저 확대해 소규모 추가 검증을 수행한다.
- 공개 벤치에서 가져온 샘플은 라이선스와 사용 조건을 확인한 뒤 별도 데이터셋으로 분리한다.
- 내부 규칙 기반 탐지 외에 문맥형 분류기나 약지도 점수화 계층을 추가해 우회 표현 대응력을 높인다.
- 행정복지센터 민원 시나리오에 맞는 비식별 실제 업무 문장으로 FP/FN 분석을 반복한다.
- 영어 공개 데이터셋 기반 재학습, threshold 조정, hard negative 확장을 통해 범용 환경 확장 가능성을 검증한다.
