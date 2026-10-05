# UI·OpenAI 통합 검증 보고서

## 작업 식별 정보

- 검증일: 2026-10-04 KST
- 원격 저장소: `https://github.com/treasonking/Capstone_Design.git`
- 기준 `master`: `7858ba0393d41f8ae9a51d757eb56d05a38e2b50`
- 기준 UI: `90910e870ff0dab320f4921b42592178ab12d955`
- 원본 보안 수정: `fd09902fdccc4d22001da46c85c3d812ac3282fd`
- 원본 OpenAI 어댑터: `5e20a767508ef9d3d93ea18f21d47121d78e9d40`
- 통합 브랜치: `codex/ui-openai-integration`
- 통합 커밋: `991c552`(보안), `6567946`(OpenAI Provider)

## 적용 결과

| 영역 | 결과 | 근거 |
|---|---|---|
| 브랜치 계보 | 통과 | 최신 UI가 `master` `7858ba0` 위에 있고 보안/API 두 커밋이 미포함임을 재확인 후 순서대로 `-x` 적용 |
| Provider | 통과 | `mock`, `openai` 고정 allowlist; 요청 본문으로 Provider·URL·모델 변경 불가; 자동 폴백 없음 |
| OpenAI 요청 | 통과(Stub) | `safe_input`, Responses API, `store=False`, timeout, 출력 토큰 상한, SDK retry 0 검증 |
| 입력 보호 | 통과 | BLOCK upstream 0회, MASK/WARN 안전 입력만 Provider 전달 |
| 출력 보호 | 통과 | Provider 응답 뒤 Validator Agent 검증 후 최종 반환 |
| 감사 로그 | 통과 | user ID 가명화, 중첩 원문 제거, HMAC key 분리, provider 메타데이터 기록 |
| UI 비동기 결함 | 통과 | UI-01~03 실행형 Node VM 테스트 추가 |
| 모바일 | 통과 | 390px 수평 오버플로 발견 후 grid 최소 너비 수정·재검증 |

## 자동 테스트

통합 전 최신 UI 기준선:

```powershell
$env:RUN_LIVE_OPENAI_TESTS = "0"
python -m pytest -q
```

- 결과: `168 passed, 8 warnings in 27.64s`

통합 후 focused 테스트:

```powershell
python -m pytest backend/tests/test_demo_ui_contract.py backend/tests/test_auth_api.py backend/tests/test_admin_api.py backend/tests/test_providers.py backend/tests/test_provider_proxy_integration.py backend/tests/test_upstream_config_api.py backend/tests/test_policy_engine.py backend/tests/test_audit_integrity.py backend/tests/test_audit_service.py -q
```

- 결과: `59 passed, 8 warnings in 12.49s`

UI 지연·중단 실행 테스트:

```powershell
node --test frontend/demo_async.test.js
```

- 결과: `9 passed, 0 failed`
- 재현 범위: header/body timeout, body read 실패, caller abort, 비JSON, 204, 인증 모드 경합, 누락 access token, 지연 화면 전환 취소, 관리자 token/logout/origin/user-session stale 응답

최종 전체 테스트:

```powershell
$env:RUN_LIVE_OPENAI_TESTS = "0"
python -m pytest -q
```

- 결과: `188 passed, 1 skipped, 8 warnings in 17.42s`
- skip: `backend/tests/test_openai_live.py` 실제 OpenAI API smoke 1건
- 경고: Starlette TestClient/httpx, FastAPI `on_event`, Joblib/NumPy 사용 중단 예정 경고. 실패로 숨기지 않았으며 이번 범위의 동작 오류는 아니다.

## 평가 재실행

정책 커밋 통합 후 평가를 임시 출력 경로로 다시 실행했다. 기존 reports의 기준 수치를 임의로 덮어쓰지 않았다.

| 데이터 | 결과 | 해석 제한 |
|---|---|---|
| `evaluation/sample_dataset.json` | PII F1 `0.935`, Injection F1 `0.920` | 내부 샘플 |
| `evaluation/external_validation_sample.json` | PII F1 `0.933`, Injection F1 `0.868` | 외부 검증 샘플, 공개 대규모 데이터셋 전체 결과가 아님 |
| `datasets/sample_dataset_v2.json` | Micro F1 `0.960`, Macro F1 `0.993` | 내부 v2 데이터셋 |

이 수치는 Provider 통합으로 성능이 향상되었다는 근거가 아니다. 외부 공개 데이터셋, external-tuned artifact와 내부 toy·회귀 데이터셋 결과를 같은 성능 주장으로 합치지 않는다.

## 로컬 HTTP·브라우저 검증

실제 외부 OpenAI 대신 로컬 Mock LLM(`8011`), FastAPI(`8010`), 정적 UI(`5510`)를 사용했다. 합성 계정과 합성 관리자 토큰만 사용했다.

- API signup/login 후 Mock `/proxy/chat`: `ALLOW`, `provider=mock`, `upstream_status=success`, Validator `PASS`
- 브라우저 로그인 후 `/proxy/analyze`: `ALLOW`, 출력/Validator `SKIPPED`
- 브라우저 Mock 프록시: 입력·출력 `ALLOW`, Validator `PASS`, provider/model/upstream 메타데이터 확인
- PII 예시: `MASK`, 마스킹 버튼 활성화, 입력이 `010-12**-****`, `us***@example.com`으로 변경됨
- 인젝션 예시: `BLOCK`, 프록시 전송 버튼 비활성화, upstream 미호출 메타데이터 확인
- 관리자 API: 합성 `X-Admin-Token`으로 통계와 최근 차단 이력 표시 확인. 첫 병렬 조회에서 in-app browser의 일시적 연결 오류가 한 번 발생했으나 HTTP 세 엔드포인트는 모두 200이었고 UI 재시도는 성공했다.
- 모바일 390px: 수정 전 `scrollWidth=1113`, `clientWidth=375`를 재현. 수정 후 둘 다 `375`, 결과 grid 폭 `305px` 확인

## 보안·구현 경계

- OpenAI API key는 UI, 응답, 감사 로그로 보내지 않는다.
- 감사 로그는 raw prompt/response, system prompt, Authorization, 개인정보 원문을 저장하지 않는다.
- 현재 감사 서명은 **ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조**다. `HMAC-SHA256-MOCK`, `MOCK_ONLY`이며 실제 PQC가 아니다.
- Validator Agent는 LLM/Mock LLM 응답 생성 후 최종 반환 전 계층이다. SSE는 버퍼링 후 검증이며 실시간 토큰 검증이 아니다.
- 실제 OpenAI API는 별도 키·모델·비용 승인 없이 호출하지 않아 미검증이다.
- Azure OpenAI, Ollama, 기타 Provider와 자동 폴백은 미구현이다.

## 판정과 남은 리스크

로컬 기준 판정은 **병합 가능**이다. 단, GitHub PR CI 성공과 리뷰 승인이 최종 병합 조건이다.

- 실제 OpenAI 계정의 모델 권한, 비용, Rate Limit, 데이터 제어는 미검증이다.
- 관리자 병렬 조회에서 브라우저 일시 오류가 한 번 있었으므로 CI 외에 배포 대상 브라우저에서 반복 smoke를 권장한다.
- 세션은 프로세스 메모리 기반이라 서버 재시작과 다중 worker 공유를 지원하지 않는다.
- 관리자 인증은 별도 토큰 방식이며 계정별 RBAC가 아니다.
- SSE 검증은 응답 전체 버퍼링으로 first-byte latency와 메모리 비용이 증가한다.

## 2026-10-05 timeout 복구 후속 검증

### 범위와 기준

- 수정 기준: `8479eebff5610e8eb2e2e871a8823d1d127d9f83`
- 작업 브랜치: `codex/ui-openai-integration`
- 범위: 로그인·회원가입·세션 복원·관리자 조회의 timeout 후 UI 복구와 재시도
- 제외: 디자인, Provider 구조, 탐지 정책·평가 데이터, 인증 방식, 감사 서명 알고리즘

기존 구현은 현재 요청 판정에 `!controller.signal.aborted`를 포함했다. `requestJson`이 timeout 때 controller를 abort하면 현재 요청까지 stale로 판정되어 `catch`의 오류 안내와 `finally`의 잠금 해제가 실행되지 않았다. 수정 전 추가 회귀 테스트에서 로그인, 회원가입, 세션 복원, 관리자 timeout 4개 경로가 실패했고 기존 stale 차단 테스트는 통과했다.

수정 후에는 작업 소유권과 성공 적용 가능성을 분리했다. timeout된 현재 작업은 오류 안내와 상태 정리를 수행하고, 명시적 취소·세대 변경·origin/토큰/세션 변경으로 소유권을 잃은 요청은 success, failure, finally 모두 새 화면을 변경하지 못한다.

### 실행 결과

```powershell
node --test frontend/demo_async.test.js
```

- 결과: `15 passed, 0 failed`
- 포함: `AUTH-TIMEOUT`, `SIGNUP-TIMEOUT`, `RESTORE-TIMEOUT`, `ADMIN-TIMEOUT`, `AUTH-STALE`, `ADMIN-STALE`, 기존 token/logout/origin/session invalidation
- fixture에서만 기본 timeout을 10ms로 줄였고 제품의 `REQUEST_TIMEOUT_MS=15000`은 유지했다.

```powershell
$env:RUN_LIVE_OPENAI_TESTS = "0"
python -m pytest backend/tests/test_demo_ui_contract.py backend/tests/test_auth_api.py backend/tests/test_admin_api.py -q
```

- 결과: `25 passed, 8 warnings in 20.56s`

```powershell
$env:RUN_LIVE_OPENAI_TESTS = "0"
python -m pytest -q
```

- 결과: `189 passed, 1 skipped, 8 warnings in 17.12s`
- skip: 실제 OpenAI API smoke 1건. 키·모델·비용 승인이 없어 실행하지 않았다.
- 경고: 기존 Starlette TestClient/httpx, FastAPI `on_event`, Joblib/NumPy 사용 중단 예정 경고다.

### 5500 브라우저 검증

수정된 실제 `frontend/demo.html`과 지연 API fixture를 동일 origin `http://127.0.0.1:5500`에서 제공했다. fixture는 합성 이메일·비밀번호·토큰만 사용했으며 제품 timeout 15초를 그대로 적용했다.

- 첫 로그인: 16초 지연으로 `요청 시간이 초과되었습니다.` 표시, 로그인 버튼·필드·탭 복구 확인
- 같은 화면에서 로그인 재시도: 성공 후 콘솔 전환 확인
- 첫 관리자 조회: 16초 지연으로 timeout 표시, 이전 통계 `-` 초기화, 새로고침 버튼과 관리자 토큰 유지 확인
- 같은 토큰으로 관리자 재조회: 총 요청 `12`, 허용 `7`, 마스킹 `2`, 경고 `1`, 차단 `2` 표시 확인
- 검증 후 임시 fixture와 에이전트가 연 탭을 닫고 기존 5500 정적 서버를 복원했다.

이번 변경은 UI의 비동기 상태 복구만 수정했으며 PII·Prompt Injection 탐지 성능, Validator Agent 동작, OpenAI Provider, 감사 로그 서명 방식에는 변화를 주지 않았다. 감사 서명은 계속 **ML-DSA 교체 가능한 감사 로그 서명 인터페이스와 Mock signer 기반 검증 구조**이며 실제 ML-DSA가 아니다.
