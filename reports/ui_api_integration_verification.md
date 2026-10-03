# UI/API 연동 검증 보고서

## 작업 식별 정보

- 기준 브랜치: `wkdnjs5665-login-signup-ui`
- 사전 검토 기준: `3cf597d80729381dff58bcb099cafad4cdfbb994`
- 구현 커밋: `06ca3e4da899c027fa960ecf0d881c626b33fc79`
- 검증일: 2026-10-04 KST
- 작업 범위: 인증·프록시·관리자 UI/API 연결, 보안 상태 표시, 회귀 테스트와 운영 문서

## 환경

| 구성 | 버전·값 |
|---|---|
| OS | Windows, PowerShell |
| Python | 3.12.14 |
| Node.js | 22.18.0 |
| FastAPI | 0.140.7 |
| Starlette | 1.3.1 |
| HTTPX | 0.28.1 |
| Pydantic | 2.13.4 |
| pytest | 9.1.1 |
| 브라우저 | Codex in-app Chromium, 데스크톱 및 390px·360px viewport |
| upstream | 로컬 `tools.mock_llm` (실제 외부 LLM 아님) |

## 실행 명령과 결과

변경 전 기준 테스트:

```powershell
python -m pytest backend/tests/test_auth_api.py backend/tests/test_proxy_analyze_api.py backend/tests/test_admin_api.py backend/tests/test_proxy_e2e.py -q
```

- 결과: `24 passed, 8 warnings`

변경 후 전체 테스트:

```powershell
python -m pytest -q
```

- 결과: `168 passed, 8 warnings in 10.23s`
- 경고: Starlette TestClient의 httpx 사용 중단 예정 1건, FastAPI `on_event` 사용 중단 예정 2건, Joblib/NumPy shape 설정 사용 중단 예정 5건
- 경고는 기존 호환성 경고이며 이번 범위에서 숨기거나 기대값을 낮추지 않았다.

추가 검사:

```powershell
node --check -
git diff --check
rg -n "BrowserTest-2026|ui-test-admin|010-1234-5678|user@example.com|browser.verify@example.test" logs/audit_log.jsonl
```

- 인라인 JavaScript 문법 검사 통과
- diff 공백 검사 통과
- 합성 비밀번호·관리자 토큰·원문 전화번호·이메일·계정 문자열이 감사 로그에 없음
- 브라우저 콘솔 error 로그 0건

## 브라우저 검증

로컬 Mock LLM(8001), FastAPI 프록시(8000), 정적 UI(5500)를 실행했다. 합성 계정 `browser.verify@example.test`와 합성 데이터만 사용했다.

- 로그인 후 콘솔 진입 및 새로고침 `/auth/me` 세션 복원 확인
- PII 사전 검사: `MASK`, 출력 `SKIPPED`, Validator `미실행`, 전화번호·이메일 상세 탐지 확인
- 마스킹 적용: 원문 `010-1234-5678`, `user@example.com`이 입력에서 제거되고 결과가 초기화됨
- Mock 프록시 전송: 입력·출력 `ALLOW`, Validator `PASS`, 상세 배열은 “미제공”, 무결성은 “이 응답에서 확인할 수 없음”으로 표시
- 인젝션 사전 검사: `BLOCK`, `INJ_DIRECT_OVERRIDE`, 전송 버튼 잠금, Validator `SKIPPED`
- BLOCK 후 입력 변경: 결과 초기화 및 전송 버튼 복구
- 관리자 토큰 실패: 401 메시지, 토큰·수치 초기화, 검색 잠금
- 관리자 토큰 성공: 전체 통계와 최근 BLOCK 이력 표시, reason_code 검색 활성화
- 로그아웃: 사용자 입력·결과·관리자 토큰 초기화, 새로고침 후 로그인 화면 유지
- 서버 재시작: 메모리 세션 무효화 후 401을 세션 만료로 표시하고 로그인 화면 이동
- 390px: viewport 390, 문서 `scrollWidth=375`, 주요 입력 폭 305px로 수평 넘침 없음
- 360px: viewport 360, 문서 `scrollWidth=345`, 결과 그리드·입력 폭 275px로 수평 넘침 없음

## 완료 기준 결과

| ID | 결과 | 근거·제한 |
|---|---|---|
| AUTH-01 | 통과 | HTTP 테스트에서 가입·중복·잘못된 로그인·422 검증. 브라우저에서는 사전 생성한 합성 계정으로 로그인 UI 검증 |
| AUTH-02 | 통과 | 브라우저 로그인·새로고침 복원·로그아웃 및 화면 데이터 정리 확인 |
| AUTH-03 | 통과 | HTTP 무인증·무효 토큰 테스트와 서버 재시작 후 브라우저 401 이동 확인 |
| SAFE-01 | 통과 | 브라우저 사전 검사 ALLOW, 백엔드 정상 프록시 회귀 테스트 |
| PII-01 | 통과 | 브라우저 MASK 미리보기·적용·재제출. 테스트에서 upstream JSON에 원문 전화번호가 없고 마스킹 문자열만 있음을 단언 |
| INJ-01 | 통과 | 브라우저 BLOCK과 버튼 잠금. 테스트에서 BLOCK 경로의 upstream 함수 호출 시 즉시 실패하도록 해 0회 호출 검증 |
| WARN-01 | 부분 검증 | 확인 대화상자 코드 경로와 정적 계약 검사는 통과. 기본 합성 입력에서 자연 발생 WARN 브라우저 사례는 미재현 |
| VAL-01 | 통과 | 사전 검사 SKIPPED와 Mock chat의 실제 Validator PASS를 브라우저에서 분리 표시 |
| ERR-01 | 부분 검증 | 401·422·관리자 미설정 503은 HTTP, 401은 브라우저에서 검증. 403·429·5xx·비JSON·시간 초과는 분기 정적 검사만 수행 |
| RACE-01 | 부분 검증 | 공유 busy 상태, AbortController, 요청 순번·입력 버전, BLOCK 유지 정적 테스트 통과. 인위적 지연을 넣은 브라우저 경합 fixture는 미실행 |
| ADMIN-01 | 통과 | 무자격·잘못된 토큰·정상 토큰·미설정 fail-closed를 HTTP/브라우저에서 확인 |
| ADMIN-02 | 통과 | 전체 통계, 최근 BLOCK 이력, reason_code 검색의 실제 표시 확인 |
| UI-01 | 통과 | 데스크톱, 390px, 360px에서 주요 조작과 수평 넘침 없음 확인 |
| PRIV-01 | 통과 | 감사 로그 서비스 테스트 및 합성 민감 문자열 검색 결과 0건 |
| XSS-01 | 부분 검증 | 동적 `innerHTML` 미사용과 `textContent` 렌더링 정적 테스트 통과. 악성 서버 응답 fixture 브라우저 실행은 미수행 |

## 구현·Mock·미검증 경계

- 실제 구현: SQLite 계정, PBKDF2 비밀번호 해시, 메모리 Bearer 세션, PII·인젝션 사전 검사, 프록시 입력 재검사, Validator 출력 검사, 관리자 토큰 서버 검증.
- Mock: upstream은 로컬 Mock LLM이다. 감사 로그는 **ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조**이며 실제 ML-DSA가 아니다.
- 미검증: 유료 외부 LLM, 다른 브라우저 엔진, WARN 자연 발생 브라우저 사례, 오류·경합용 브라우저 fixture 전체 조합.
- 세션 제한: 서버 재시작 시 로그아웃되고, 공유 저장소 없이 다중 worker 세션을 지원하지 않는다.
- 관리자 제한: 별도 `X-Admin-Token` 방식이며 계정별 RBAC가 아니다.
