# UI와 API 연결 구조

## 범위

`frontend/demo.html`은 기존 블랙·화이트 발표용 디자인을 유지하면서 FastAPI의 인증, 사전 검사, 프록시, 관리자 API를 호출한다. 프런트엔드는 외부 LLM을 직접 호출하지 않으며 외부 LLM API 키를 보관하지 않는다.

이번 연결 작업은 탐지 규칙, 학습 데이터, 평가 수치를 변경하지 않았다. Validator Agent와 감사 로그 무결성 구현도 변경하지 않았다. 감사 로그 무결성은 실제 ML-DSA 구현이 아니라 **ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조**다.

## 인증과 API origin

- 로그인 전 `API Base URL`을 설정한다.
- 로그인 성공 시 Bearer 토큰과 인증에 성공한 API origin을 `sessionStorage`에 저장한다.
- 사용자 토큰은 저장된 origin과 요청 origin이 정확히 일치할 때만 전송한다.
- 로그인 후 API 주소를 바꾸면 로컬 인증, 관리자 상태, 입력과 결과를 지우고 재로그인을 요구한다.
- `/auth/me`의 401은 만료·무효 세션으로 처리해 토큰을 지운다. 네트워크 실패나 시간 초과는 세션 만료로 가장하지 않으며 로컬 토큰을 유지한다.
- 로그아웃은 먼저 `/auth/logout`으로 서버 토큰 폐기를 시도한 뒤 로컬 상태를 지운다. 서버 호출 실패 시 서버 폐기 미확인을 별도로 알린다.

계정은 SQLite에 저장하지만 세션은 서버 프로세스 메모리에 저장된다. 따라서 서버 재시작 시 재로그인이 필요하고, 별도 공유 세션 저장소 없이 여러 worker를 사용하면 worker 간 세션이 공유되지 않는다.

## API 필드 대응

| 화면 표시 | `/proxy/analyze` | `/proxy/chat` |
|---|---|---|
| 최종 조치 | 최상위 `action` | 최상위 `action` 또는 `audit_summary.final_action` |
| 입력 조치 | `audit_summary.input_action`을 우선 사용하고 없으면 `action` | 최상위 `input_action` 또는 `audit_summary.input_action` |
| 출력 조치 | `audit_summary.output_action`, 정상적으로 `SKIPPED` | 최상위 `output_action` 또는 `audit_summary.output_action` |
| 입력 PII·Injection | 최상위 `pii_detected`, `injection_detected` | `audit_summary.input.pii_detected`, `injection_detected` |
| 출력 PII·Injection | LLM 미호출이므로 `SKIPPED` | `audit_summary.output`의 요약 필드 |
| 상세 탐지 | 최상위 `detector_results` | 현재 응답 계약에는 없음. “미제공”으로 표시 |
| Validator | `audit_summary.validator.validator_result=SKIPPED` | 실제 `validator_result`가 있을 때만 “실행됨” 표시 |
| 감사 무결성 | `audit_summary.integrity`가 없으면 “이 응답에서 확인할 수 없음” | 동일 |

서명이 있다는 사실만으로 검증 성공을 표시하지 않는다. `verified=true`, `verified=false`, 서명만 제공됨, 정보 미제공을 구분한다. 현재 공개 프록시 응답은 일반적으로 무결성 정보를 포함하지 않으며, UI를 위해 새 공개 감사 조회 API를 추가하지 않았다.

## 요청 상태와 오류 처리

- 분석과 전송은 하나의 진행 상태를 공유한다. 진행 중 버튼·입력·정책·API 주소를 잠근다.
- 요청마다 입력 버전과 순번을 기록해 오래된 응답이 현재 입력 결과를 덮어쓰지 못하게 한다.
- 입력 또는 정책이 바뀌면 이전 검사와 BLOCK 상태를 무효화하고 결과 화면을 초기화한다.
- BLOCK 결과는 요청 `finally`에서 해제하지 않는다. 현재 입력을 수정해야 전송 버튼이 다시 열린다.
- MASK 적용은 실제 입력과 글자 수를 갱신하고 이전 검사 결과를 무효화한다. 이후 사전 검사 또는 `/proxy/chat`의 서버 재검사를 거친다.
- WARN은 사용자가 확인 대화상자에서 계속 진행을 선택해야 프록시 전송을 시작한다. 백엔드는 전송 때 입력을 다시 검사한다.
- 401, 403, 409, 422, 429, 5xx, JSON이 아닌 응답, 네트워크 실패, 취소, 시간 초과를 구분한다.
- FastAPI validation error 배열은 필드와 메시지 목록으로 정규화한다.
- 서버 제공 값은 `textContent` 또는 DOM 노드의 `textContent`로 렌더링한다. 서버 오류 본문, 토큰, 비밀번호, 키, 스택 트레이스를 콘솔이나 결과 화면에 출력하지 않는다.

## 관리자 접근

- 모든 `/admin/*` 요청은 서버에서 `X-Admin-Token`과 `ADMIN_API_TOKEN`을 비교한다.
- 공개 기본 토큰은 없다. `ADMIN_API_TOKEN`이 없거나 빈 문자열이면 서버는 503으로 안전하게 접근을 거부한다.
- 관리자 토큰은 비밀번호 입력 필드의 페이지 메모리에만 있고 브라우저 저장소에는 저장하지 않는다.
- 인증 전에는 통계·검색·차단 이력을 잠근다. 인증 실패, 로그아웃, 사용자 세션 초기화 때 관리자 토큰과 캐시 데이터를 지운다.
- `/admin/recent-blocks`는 BLOCK만 반환하므로 UI는 상태 필터를 제공하지 않고 reason_code 검색만 제공한다.
- 전체 감사 로그 통계와 최근 제한된 차단 이력의 범위를 화면에서 구분한다.

이 방식은 별도 관리자 토큰 방식이며 계정별 역할 관리(RBAC)가 구현되었다는 뜻이 아니다. 사용자 계정에 관리자 역할을 부여하고 권한을 회수하는 기능은 후속 과제다.

## 구현·Mock·미검증 경계

| 구분 | 상태 |
|---|---|
| 인증·사전 검사·프록시·관리자 HTTP 연결 | 구현 및 로컬 브라우저 검증 |
| PII·Prompt Injection 탐지와 정책 처리 | 기존 구현 재사용, 회귀 테스트 |
| Validator Agent | Mock LLM 응답 생성 후 최종 반환 전의 기존 출력 검증 계층 재사용 |
| upstream | 로컬 Mock LLM으로 검증 |
| 외부 LLM | API 키와 별도 승인 없이 호출하지 않아 미검증 |
| WARN 자연 발생 | 이번 브라우저 실행에서는 재현하지 않음. 코드 경로와 정적 계약 검사만 수행 |
| 감사 로그 서명 | 기존 Mock signer 기반 구조 유지. 실제 ML-DSA 아님 |
| 브라우저 | 로컬 in-app Chromium 환경에서 검증. 다른 브라우저 호환성은 미검증 |
