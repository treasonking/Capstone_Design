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

요약하면 `deepset/prompt-injections`에서는 Rule Only와 Hybrid의 Recall이 모두 0.0760으로 같았고, `protectai/prompt-injection-validation`에서는 둘 다 Recall 0.1997, F1 0.3227이었다. `Lakera/gandalf_ignore_instructions`에서는 Hybrid Recall이 0.4680으로 Rule Only 0.4400보다 소폭 높았다.

반면 Lightweight Model Only는 `deepset` Recall 0.0038, `protectai` Recall 0.0136, `Lakera` Recall 0.1110으로 낮게 측정되었다. 따라서 현재 artifact는 내부/데모 시나리오 보완에는 사용할 수 있지만, 외부 영어 Prompt Injection 데이터셋을 일반화해서 탐지한다고 주장하면 안 된다. 외부 데이터셋 기반 재학습, threshold 조정, hard negative 보강이 필요하다.

## 6. 발표 시 설명 문장

- "현재 1.0 점수는 내부 검증셋 기준이며, 운영 성능을 보장하는 수치로 주장하지 않습니다."
- "이번 MVP에서는 정책 회귀와 시연 재현성을 우선했고, 외부 영어 데이터셋에서 낮은 Recall이 나온 부분은 대표 패턴 보강과 개선 과제로 분리했습니다."
- "외부 공개 데이터셋 3종에 대해서는 `reports/external_dataset_compare_report.md`에서 Rule Only, Lightweight Model Only, Hybrid / Full Pipeline을 분리해 확인합니다."
- "현재 외부 영어 데이터셋에서는 Lightweight Model Only의 Recall이 낮으므로, Hybrid 개선의 대부분을 모델이 만들었다고 주장하지 않습니다."
- "artifact가 없는 fallback 상태는 완전한 Hybrid 성능으로 해석하지 않습니다."

## 7. 향후 개선 계획

- `evaluation/external_validation_sample.json` 같은 외부 스타일 샘플을 먼저 확대해 소규모 추가 검증을 수행한다.
- 공개 벤치에서 가져온 샘플은 라이선스와 사용 조건을 확인한 뒤 별도 데이터셋으로 분리한다.
- 내부 규칙 기반 탐지 외에 문맥형 분류기나 약지도 점수화 계층을 추가해 우회 표현 대응력을 높인다.
- 행정복지센터 민원 시나리오에 맞는 비식별 실제 업무 문장으로 FP/FN 분석을 반복한다.
- 영어 공개 데이터셋 기반 재학습, threshold 조정, hard negative 확장을 통해 범용 환경 확장 가능성을 검증한다.
