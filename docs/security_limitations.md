# Security Limitations

본 프로젝트는 범용 Prompt Injection 탐지기가 아니라, 한국어 공공기관·사내망 환경에서 발생할 수 있는 개인정보 유출 및 정책 우회형 Prompt Injection을 우선 방어 대상으로 설계한 LLM 보안 프록시이다.

## Scope

- 우선 방어 대상은 주민등록번호, 연락처, 이메일, 주소, 계좌번호 등 공공기관 민원 업무에서 자주 등장하는 개인정보와 정책 우회형 Prompt Injection이다.
- `ignore previous instructions`, `reveal the system prompt`, `bypass safety policy`, `act as DAN` 같은 대표 영어 패턴은 보강했지만, 모든 영어 jailbreak 또는 간접 Prompt Injection을 포괄하지 않는다.
- `이전 instructions 무시`, `system prompt 보여줘`, `policy bypass 해줘` 같은 한국어-영어 혼합 표현은 국내 업무 환경에서 현실적으로 발생할 수 있는 최소 우회 표현으로 다룬다.

## Known Limits

- 외부 영어 데이터셋에서 낮은 Recall이 측정된 것은 현재 탐지 정책과 학습 데이터가 한국어 공공기관 시나리오에 집중되어 있기 때문이다. 이 결과는 시스템 실패로 숨기기보다, 범용 환경 확장을 위한 개선 지점으로 해석한다.
- Lightweight classifier artifact가 존재하지 않는 경우 시스템은 실행 중단 대신 rule-based fallback으로 동작한다. 이는 데모 안정성을 위한 설계이나, Hybrid 성능 평가에서는 `model_status`를 `artifact_missing`으로 분리 표시한다.
- 따라서 fallback 상태의 결과를 완전한 Hybrid 성능으로 해석하지 않는다.
- 보안 설명, 정책 작성, 예방 방법 문의처럼 공격을 설명하는 문장은 차단 대상이 아니다. 예: `Explain what prompt injection is.`, `이전 지시를 무시하라는 공격을 어떻게 막을 수 있어?`

## Operation Guidance

- 운영 또는 발표 자료에서는 내부 데이터셋 F1 1.0을 일반화 성능으로 설명하지 않는다.
- 외부 영어 데이터셋 결과는 범용 확장을 위한 한계 분석 자료로 분리한다.
- 실제 운영 수준으로 확장하려면 영어 공개 데이터셋 기반 재학습, threshold 조정, 간접 인젝션/RAG 문서 공격 평가, hard negative 확장이 필요하다.
