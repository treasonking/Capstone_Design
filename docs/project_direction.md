# Capstone Design 방향 정리

## 목적
- 내부망 환경에서도 생성형 AI를 안전하게 활용할 수 있도록 `LLM 보안 프록시`를 구축한다.
- 입력/출력/로그를 정책 기반으로 통제하여 개인정보 유출 및 정책 위반 위험을 낮춘다.

## 핵심 흐름
1. 사용자 UI 요청 수신
2. 보안 프록시에서 입력 검사
3. 탐지 엔진(PII, Prompt Injection) 실행
4. 정책 엔진으로 `ALLOW / WARN / MASK / BLOCK` 결정
5. 허용된 경우에만 LLM 호출
6. 출력 재검사 후 사용자 반환
7. 감사 로그 저장

## 정책 모드
- `ALLOW`: 그대로 통과
- `WARN`: 경고 후 통과 또는 재입력 유도
- `MASK`: 민감정보 일부 마스킹 후 통과
- `BLOCK`: 요청 차단

## 감사 로그 원칙
- 저장: `request_id`, `user_id`, `timestamp`, `action`, `reason_codes`, 탐지 여부, `latency`, upstream 호출 여부
- 미저장: 원문 프롬프트/원문 응답/API 키/민감정보 원문

## 기술 스택(초안)
- Backend: FastAPI, Pydantic
- Detection: Presidio + 커스텀 룰(PII, Prompt Injection)
- Policy: YAML 기반 정책
- DB: SQLite(기본), PostgreSQL(확장)
- Frontend: React + Vite
- LLM 연동: OpenAI / Azure OpenAI / Ollama / Mock
- Testing: pytest, k6

## 역할 분담(초안)
- 정책/탐지 리드: 정책 포맷, reason_code, 탐지/마스킹, 정량 평가
- 게이트웨이/프록시 리드: 프록시 API, LLM 연동, 요청 추적, 예외 처리
- 성능/증빙 리드: 원문 미저장 검증, 부하테스트, 성능 지표
- QA/통합 리드: 데이터셋/라벨링, E2E 자동화, 기대값 비교 리포트
