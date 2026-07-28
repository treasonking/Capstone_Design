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
- Validator Agent는 정책 결정 재검증을 위한 운영형 확장 요소이며, 본 연구의 핵심 정량 평가 대상이 아니다. 적용 전후 오탐·미탐 변화와 latency 평가는 후속 연구로 둔다.
- PQC 기반 감사로그 서명 구조는 탐지 성능 향상 요소가 아니라 감사로그 무결성 확장 요소이다. 현재 구현은 ML-DSA 교체 가능한 인터페이스와 Mock signer 기반 검증 구조이며, 실제 PQC 알고리즘 적용 및 성능 평가는 후속 연구로 둔다.
- SSE 경로도 upstream 응답 전체를 메모리에 버퍼링한 뒤 검증한다. 검증 전 원본 토큰 노출을 막는 대신 first-byte latency와 메모리 사용량이 증가하며, 대용량 응답 제한은 별도 운영 정책이 필요하다.
- 감사 로그의 개발용 signer는 HMAC-SHA256 Mock 구현이다. 기본 개발 키와 기본 `user_id` salt는 공개된 fallback 값이므로 운영 보안을 제공하지 않는다. 비운영 환경 밖에서는 `AUDIT_LOG_HMAC_KEY`, `AUDIT_USER_ID_SALT`를 별도 비밀 관리 체계에서 주입해야 한다.
- `user_id`는 저장 전에 HMAC 기반 가명값으로 바뀌지만, salt가 유출되거나 식별자 후보 공간이 작으면 사전 대입 위험이 남는다.
- 기본 경량 분류 artifact와 external-tuned artifact가 서로 다른 scikit-learn 버전에서 만들어졌다. 직렬화 artifact는 버전 호환성 경고 없이 로드되는 버전에서 재학습·고정하고 해시와 학습 메타데이터를 함께 배포해야 한다.
- 외부 held-out split에는 train/eval 정규화 텍스트 해시 중복 42건이 남아 있어 external-tuned 수치가 낙관적일 수 있다.

## Operation Guidance

- 운영 또는 발표 자료에서는 내부 데이터셋 F1 1.0을 일반화 성능으로 설명하지 않는다.
- 외부 영어 데이터셋 결과는 범용 확장을 위한 한계 분석 자료로 분리한다.
- 실제 운영 수준으로 확장하려면 영어 공개 데이터셋 기반 재학습, threshold 조정, 간접 인젝션/RAG 문서 공격 평가, hard negative 확장이 필요하다.
- Validator Agent와 PQC를 탐지 성능을 높이는 핵심 기법처럼 설명하지 않는다. 두 요소는 운영 환경에서 정책 결정의 신뢰성, 감사 가능성, 로그 무결성을 높이기 위한 확장 요소로 설명한다.
- 기존 로컬 `logs/audit_log.jsonl`에는 서명 도입 전 또는 구형 포맷 레코드가 섞일 수 있다. 배포 시 로그 스키마 버전과 키 ID별 검증·보존·마이그레이션 정책을 정의해야 한다.
