# Capstone Design - Policy/Detection MVP

공공기관·사내망 환경의 LLM 보안 프록시를 위한 **정책/탐지/마스킹/평가 코드베이스** 초안입니다.  
이 저장소는 전체 프록시를 완성하기보다, 캡스톤 시연에 필요한 설명 가능하고 재현 가능한 Rule-based MVP에 집중합니다.

## 내 역할(정책/탐지 리드) 반영 범위

- YAML 기반 정책 포맷(`ALLOW/WARN/MASK/BLOCK`, 우선순위, threshold)
- PII 탐지(정규식 기반)
- Prompt Injection 탐지(한/영 혼합 룰)
- 정책 엔진(최종 action 결정, reason code 집계)
- 마스킹 유틸(부분 마스킹)
- 정량 평가(precision/recall/F1, FP/FN)
- pytest 테스트

## 디렉토리 구조

```text
backend/
  app/
    detection/
      models.py
      reason_codes.py
      pii_detector.py
      injection_detector.py
    engine/
      masking.py
      policy_engine.py
  tests/
    test_pii_detector.py
    test_injection_detector.py
    test_masking.py
    test_policy_engine.py
policies/
  policy.yaml
evaluation/
  sample_dataset.json
  evaluate.py
  report_generator.py
README.md
```

## 파일별 책임

- `backend/app/detection/models.py`: 탐지 결과, 정책 결과, 액션 Enum 데이터 모델
- `backend/app/detection/reason_codes.py`: reason_code 표준 집합
- `backend/app/detection/pii_detector.py`: 이메일/휴대전화/주민번호/계좌 유사 패턴 탐지
- `backend/app/detection/injection_detector.py`: 프롬프트 인젝션 룰 탐지
- `backend/app/engine/masking.py`: reason_code별 부분 마스킹 함수
- `backend/app/engine/policy_engine.py`: `policy.yaml` 로딩 + 우선순위 기반 최종 판정
- `policies/policy.yaml`: 정책 모드, 우선순위, threshold 샘플
- `evaluation/evaluate.py`: 데이터셋 기반 PII/Injection 분리 평가
- `evaluation/report_generator.py`: 평가 결과 Markdown 리포트 생성
- `backend/tests/*`: 주요 모듈 단위 테스트

## 빠른 실행

1. 의존성 설치

```bash
pip install pyyaml pytest
```

2. 테스트 실행

```bash
pytest -q
```

3. 정량 평가 + 리포트 생성

```bash
python -m evaluation.evaluate \
  --dataset evaluation/sample_dataset.json \
  --report evaluation/evaluation_report.md
```

## 정책 엔진 동작 요약

1. PII/Injection 탐지기로 `DetectionResult` 목록 생성
2. `policy.yaml`에서 reason_code별 rule(action, priority, threshold) 조회
3. threshold를 넘는 탐지만 후보로 채택
4. 우선순위(priority, action severity) 기준으로 최종 action 결정
5. `MASK`면 마스킹 텍스트 생성, 그 외는 원문 유지/차단
6. 이유(reasons)와 audit summary를 함께 반환

## 확장 포인트

- Presidio 연동: `detect_pii` 내부에 analyzer adapter 추가
- 정책 버전 관리: policy 파일 다중화 + policy_id 매핑
- 프록시 연동: 기존 FastAPI 프록시 입력/출력 단계에 `evaluate_policy` 연결
- 리포트 확장: HTML 리포트 및 confusion matrix 추가

