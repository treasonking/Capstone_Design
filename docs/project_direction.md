# Capstone Design 방향 정리

## 목적
- 동사무소/행정복지센터 환경에서도 생성형 AI를 안전하게 활용할 수 있도록 `LLM 보안 프록시`를 구축한다.
- 입력/출력/로그를 정책 기반으로 통제하여 개인정보 유출 및 정책 위반 위험을 낮춘다.

## 핵심 흐름
1. 사용자 UI 요청 수신
2. 보안 프록시에서 입력을 다층형 탐지 파이프라인으로 전달
3. 정규식 패턴 계층에서 정형 PII 우선 탐지
4. 휴리스틱 규칙 계층에서 정책 우회, 시스템 프롬프트 탈취, 지시 무시 단서 탐지
5. 경량 분류 계층에서 비정형 또는 애매한 문장형 공격 보완 분류
6. 의사결정 계층에서 `ALLOW / WARN / MASK / BLOCK` 결정
7. 허용된 경우에만 LLM 호출
8. 출력 재검사 후 사용자 반환
9. 감사 로그 저장

## 정책 모드
- `ALLOW`: 그대로 통과
- `WARN`: 경고 후 통과 또는 재입력 유도
- `MASK`: 민감정보 일부 마스킹 후 통과
- `BLOCK`: 요청 차단

## 행정복지센터 주요 보호 대상

- 주민등록번호, 연락처, 주소
- 민원번호, 세대정보, 계좌번호
- 내부 응대 기준, 정책 우선순위, 시스템 프롬프트

## 감사 로그 원칙
- 저장: `request_id`, `user_id`, `timestamp`, `action`, `reason_codes`, 탐지 여부, `latency`, upstream 호출 여부
- 미저장: 원문 프롬프트/원문 응답/API 키/민감정보 원문

## 탐지 구조

- 대표 명칭: 다층형 탐지 파이프라인(Multi-layered Detection Pipeline)
- 1계층: Regex Pattern Layer
- 2계층: Heuristic Rule Layer
- 3계층: Lightweight Classification Layer
- 4계층: Decision Layer

## 프록시 배포 형태

본 프로젝트의 프록시는 사용자 PC에 설치되는 단순 클라이언트가 아니라, 사용자 요청과 외부 LLM API 또는 내부 LLM 사이에 위치하는 서버형 보안 게이트웨이다. 기관 내부 서버 또는 컨테이너 환경에 배포할 수 있으며, 직원의 LLM 요청은 프록시를 거쳐 입력 검사, 출력 검사, 마스킹, 차단, 감사 로그 기록 과정을 수행한다.

```text
공공기관 직원 → LLM Security Proxy Server → 외부 LLM API 또는 내부 LLM
```

## 기술 스택(초안)
- Backend: FastAPI, Pydantic
- Detection: Regex Pattern Layer + Heuristic Rule Layer + Lightweight Classification Layer
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
