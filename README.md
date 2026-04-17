# Capstone Design - LLM Security Proxy MVP

공공기관/사내망 환경에서 LLM 사용 시 개인정보 유출과 프롬프트 인젝션을 줄이기 위한
정책/탐지 중심 MVP 코드베이스입니다.

## 벤치마크 요약 (예시)

> `evaluation/sample_dataset.json` 기준 샘플 결과

| 항목 | Precision | Recall | F1 | TP / FP / FN |
|---|---:|---:|---:|---:|
| PII Detection | 1.000 | 0.667 | 0.800 | 2 / 0 / 1 |
| Prompt Injection Detection | 1.000 | 1.000 | 1.000 | 3 / 0 / 0 |

## 아키텍처

```mermaid
flowchart LR
    U["User UI"] --> P["Security Proxy API"]
    P --> D["Detection Layer<br/>PII + Prompt Injection"]
    D --> E["Policy Engine<br/>ALLOW/WARN/MASK/BLOCK"]
    E -->|ALLOW/WARN/MASK| L["LLM Upstream"]
    E -->|BLOCK| X["Blocked Response"]
    L --> O["Output Re-Scan"]
    O --> E2["Policy Engine (Output)"]
    E2 --> R["Client Response"]
    P --> A["Audit Summary / Safe Logs"]
```

## 핵심 범위

- YAML 정책 기반 판정 (`ALLOW`, `WARN`, `MASK`, `BLOCK`)
- PII 탐지 (이메일, 휴대전화, 주민번호, 계좌 유사 패턴)
- Prompt Injection 탐지 (한/영 룰 기반)
- 마스킹 유틸 및 정책 엔진
- 정량 평가(precision/recall/F1)
- 프록시 입력/출력 단계 정책 적용
- pytest 테스트

## 프로젝트 구조

```text
backend/
  app/
    api/
      proxy.py
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
    test_proxy_api.py
policies/
  policy.yaml
evaluation/
  sample_dataset.json
  evaluate.py
  report_generator.py
```

## 프록시 동작 흐름 (`backend/app/api/proxy.py`)

1. 입력 텍스트를 PII + Injection 탐지
2. `policy.yaml`로 입력 단계 action 결정
3. `BLOCK`이면 즉시 차단, `MASK`면 마스킹 후 LLM 호출
4. LLM 응답을 다시 탐지/정책 평가
5. 출력이 `BLOCK`이면 차단, `MASK`면 마스킹 후 반환
6. 응답에 `action`, `input_action`, `output_action`, `reasons`, `audit_summary` 포함

## 실행 방법

1. 의존성 설치

```bash
pip install fastapi httpx pyyaml pytest
```

2. 테스트 실행

```bash
pytest -q
```

3. 평가 실행

```bash
python -m evaluation.evaluate \
  --dataset evaluation/sample_dataset.json \
  --report evaluation/evaluation_report.md
```

## 확장 아이디어

- Presidio 어댑터 추가
- 정책 버전/테넌트별 정책 파일 분리
- 감사 로그 저장소 연계 (원문 미저장 원칙 유지)
- FastAPI 실제 라우터 + 인증 미들웨어 통합
